import json

from bs4 import BeautifulSoup
from flask import current_app
from requests import get

from pyctogram import appLog, db
from pyctogram.model import Account, List, Media, User


def get_account_data(account_name, headers):
    # This function gets account data from the account_name
    # Returns : account data, if account_name exists
    #           None, if not
    url = f'https://instagram.com/{account_name}'
    try:
        response = get(url, headers=headers, timeout=5)
    except Exception as e:
        appLog.error('Something happened with the connection that '
                     f'prevented us to get {account_name}’s info - '
                     f'error: {e.args}')
        return None
    if response.status_code >= 400:
        appLog.error('Something happened with the connection that '
                     f'prevented us to get {account_name}’s info '
                     f'(Instagram status code: {response.status_code})')
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    scripts = soup.find_all('script')
    for script in scripts:
        if script.text.startswith('window._sharedData'):
            json_start = script.text.find('{')
            json_end = script.text.rfind('}') + 1
            obj = script.text[json_start:json_end]

            try:
                data = json.loads(obj)
                account_data = data['entry_data']['ProfilePage'][0]['graphql'][
                    'user']
                return account_data
            except Exception as e:
                appLog.error(f'Could not load account data - error: {e.args}')

    return None


def create_accounts(contacts_to_import, current_user, list_info):
    total = 0
    not_imported = []
    for contact in contacts_to_import:
        account = Account.query.filter_by(
            account_name=contact).first()
        if not account:
            account_data = get_account_data(contact,
                                            current_app.config[
                                                'DEFAULT_HEADERS'])

            if not account_data:
                not_imported.append(contact)
                continue

            account = Account(account_id=account_data['id'],
                              account_name=account_data['username'])
            account = update_user(account, account_data)
            account.last_updated = 0
            account.is_private = account_data['is_private']
            db.session.add(account)

        default_list = List.query.filter_by(
            user_id=current_user.id,
            shortname=list_info['shortname']
        ).first()

        # Note: default list (feed) should exist
        if not default_list:
            default_list = List(
                user_id=current_user.id,
                shortname=list_info['shortname'],
                longname=list_info['longname'],
                description=list_info['description'],
            )
            default_list.is_default = True
            db.session.add(default_list)

        if account not in current_user.accounts:
            current_user.accounts.append(account)
            total += 1

        if account not in default_list.accounts:
            default_list.accounts.append(account)

    db.session.commit()
    return total, not_imported


def get_media_sidecar(media_shortcode):
    url = f'https://instagram.com/p/{media_shortcode}'
    try:
        response = get(url,
                       headers=current_app.config['DEFAULT_HEADERS'],
                       timeout=5)
    except Exception as e:
        appLog.error('Error: Something happened with the connection that '
                     f'prevented us to get {media_shortcode}’s info'
                     f' - error: {e.args}')
        return None
    if response.status_code >= 400:
        appLog.error('Error: Something happened with the connection that '
                     f'prevented us to get {media_shortcode}’s info '
                     f'(Instagram status code: {response.status_code})')
        return None

    soup = BeautifulSoup(response.text, 'html.parser')

    scripts = soup.find_all('script')
    for script in scripts:
        if script.text.startswith('window._sharedData'):
            json_start = script.text.find('{')
            json_end = script.text.rfind('}') + 1
            obj = script.text[json_start:json_end]

            try:
                data = json.loads(obj)
            except Exception as e:
                appLog.error(f'Could not load account data - error: {e}')
                return None

            try:
                sidecar_data = data['entry_data']['PostPage'][0]['graphql'][
                    'shortcode_media']['edge_sidecar_to_children']['edges']
                return sidecar_data
            except KeyError:
                return None


def update_user(account, account_data):
    account.full_name = account_data['full_name']
    account.biography = account_data['biography']
    account.profile_pic_url = account_data[
        'profile_pic_url']
    account.profile_pic_url_hd = account_data[
        'profile_pic_url_hd']
    account.external_url = account_data['external_url']
    account.external_url_linkshimmed = account_data[
        'external_url_linkshimmed']
    account.followed_by = account_data['edge_followed_by'][
        'count']
    account.follow = account_data['edge_follow']['count']
    return account


def add_media(account, account_data):
    latest_timestamp = \
        account_data['edge_owner_to_timeline_media']['edges'][0]['node'][
            'taken_at_timestamp']

    media_count = 0

    account = update_user(account, account_data)

    for media in account_data['edge_owner_to_timeline_media']['edges']:
        node = media['node']

        # check if media has been uploaded after the latest upload from
        # this account
        if (node['taken_at_timestamp'] > account.last_updated and node[
                '__typename'] in ['GraphImage', 'GraphVideo', 'GraphSidecar']):

            # get caption
            caption = ''
            for caption_edge in node['edge_media_to_caption']['edges']:
                caption += caption_edge['node']['text']

            # get thumbnails
            thumbnails = (json.dumps(node['thumbnail_resources'])
                          if 'thumbnail_resources' in node else '')

            # check if there are some 'sidecar' images
            sidecar = ''
            if node['__typename'] == 'GraphSidecar':
                sidecar = json.dumps(get_media_sidecar(
                    media_shortcode=node['shortcode']))

            media = Media.query.filter_by(id=node['id']).first()
            if not media:
                media = Media()
                media.id = node['id']
                media.owner = node['owner']['id']
                db.session.add(media)
            media.media_type = node['__typename']
            media.is_video = node['is_video']
            media.display_url = node['display_url']
            media.caption = caption
            media.shortcode = node['shortcode']
            media.timestamp = node['taken_at_timestamp']
            media.likes = node['edge_liked_by']['count']
            media.comments = node['edge_media_to_comment']['count']
            media.thumbnails = thumbnails  # JSON object containing thumbnails  # noqa
            media.sidecar = sidecar  # JSON object containing the whole edge_sidecar_to_children.edges  # noqa

            try:
                db.session.commit()
                media_count += 1
            except Exception as e:
                appLog.error('Error: Adding an image by '
                             f'{account_data["username"]} into '
                             f'the database failed - error {e.args}')

    account.last_updated = latest_timestamp
    db.session.commit()

    return media_count


def update_media(user_id=None, list_id=None):
    if list_id:
        the_list = List.query.filter_by(id=list_id).first()
        if not the_list:
            appLog.error(f'List {list_id} does not exit. No media update')
            return None
        accounts = the_list.accounts
    elif user_id:
        user = User.query.filter_by(id=user_id).first()
        if not user:
            appLog.error(f'User {user_id} does not exit. No media update')
        accounts = user.accounts
    else:
        accounts = Account.query.all()

    account_count = 0
    total_media_added = 0
    failed_accounts = []

    # TODO: add progress bar
    for account in accounts:
        account_data = get_account_data(account.account_name,
                                        current_app.config[
                                            'DEFAULT_HEADERS'])

        if not account_data:
            status = f'🤷‍♀ Account {account.account_name} has returned no data'
            appLog.info(status)
            failed_accounts.append(account.account_name)
            continue

        if not account_data['is_private'] and \
                account_data['edge_owner_to_timeline_media']['count'] > 0:
            media_added = add_media(account, account_data)
            if media_added > 0:
                status = (f'🙋‍♀ Added {media_added} media '
                          f'for {account.account_name}')
                account_count += 1
            else:
                status = f'🙅‍♀ No new media for {account.account_name}'
            appLog.info(status)

            total_media_added += media_added

    if account_count > 0:
        s = 's' if account_count > 1 else ''
        appLog.info(f'We got {total_media_added} new media'
                    f' from {account_count} account{s}')
    else:
        appLog.info('No new media were found at this time')

    return failed_accounts
