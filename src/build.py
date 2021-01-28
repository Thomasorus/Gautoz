
import argparse
import glob
import os
import re
import shutil
import subprocess
import sys
from datetime import datetime


# Import local files
mistune = __import__('mistune')
config = __import__('config')


# Activating the renderer
renderer = mistune.Renderer()
markdown = mistune.Markdown(renderer=renderer)


# Checking for dev command
parser = argparse.ArgumentParser()
parser.add_argument(
    "-p", "--prod", help="Prints the supplied argument.", action="store_true")
args = parser.parse_args()

# Declaring build url that will be used in several parts of the app
build_url = config.relative_build_url
if args.prod:
    build_url = config.absolute_build_url


# Generates html files in the site folder, using the entries and the template.
def generate_html_pages(site_folder, entries, template, sub_pages_list, template_nav):
    for entry in entries:
        page_template = template.replace('page_title', entry['title'])

        # Checking if the page is root of a folder
        if entry["file"] == "index":

            # If root page
            # Concatenate the content of the index page with the listing of sub-pages
            # Remove "page_date" from template
            # Replaces "page_body" with the page content in the template
            entry["pageContent"] = entry["pageContent"] + sub_pages_list
            page_template = page_template.replace('page_date', "")
            page_template = page_template.replace(
                'page_body', entry['pageContent'])
        else:
            # If content page
            # Replaces "page_body" with the page content in the template
            # Replaces "page_date" with the page date in the template
            page_template = page_template.replace(
                'page_body', entry['pageContent'])
            page_template = page_template.replace(
                'page_date', "<date>" + entry['date'] + "</date>")

        # Creating navigation
        url_link = build_url
        url_text = entry['parent_text']

        if entry["parent_url"] == "":
            # If index page, return to the home
            url_link = build_url
        else:
            # If content page, return to parent page
            url_link = build_url + entry['parent_url']

        nav_template = open(template_nav, 'r').read()
        nav_html = nav_template.replace("link_url", url_link)
        nav_html = nav_html.replace("text_url", url_text)
        page_template = page_template.replace('page_navigation', nav_html)

        # Replaces all occurrences of build_url in the template files (assets, urls, etc)
        page_template = page_template.replace('build_url', build_url)

        page_template = page_template.replace('site_name', config.site_name)
        page_template = page_template.replace(
            'site_meta_description', config.site_meta_description)
        page_template = page_template.replace(
            'twitter_name', config.twitter_name)

        # Checking if content folder exists
        folderExists = os.path.exists(site_folder+entry['folder'])
        # If not, create it
        if folderExists == False:
            os.mkdir(site_folder+entry['folder'])

        # Write the HTML file
        pageFile = open(site_folder + entry['slug'], "w")
        pageFile.write(page_template)
        pageFile.close()

    print("All pages created!")


# Get title by parsing and cleaning the first line of the markdown file
def get_entry_title(page):
    pageContent = open(page, 'r')
    textContent = pageContent.read()
    textContent = textContent.splitlines()
    textContent = textContent[0]
    textContent = textContent.replace('# ', '')
    return textContent


# Get the slug from the markdown file name
def get_entry_slug(page):
    slug = page.split("/")[-1]
    slug = re.sub('\.md$', '', slug)
    if slug:
        return slug
    else:
        return ''


# From the list of files, creates the main array of entries that will be processed later
def create_entries(pages):
    fullContent = []
    for page in pages:
        tempPage = {}

        # Process the page with dedicated functions
        path = clean_path(page)
        title = get_entry_title(page)
        pageContent = markdown(open(page, 'r').read())

        # Create the page object with all the informations we need
        tempPage['slug'] = path["slug"]
        tempPage['file'] = path['file']
        tempPage['folder'] = path["folder"]
        tempPage['parent_url'] = path['parent_url']
        tempPage['parent_text'] = path['parent_text']
        tempPage['date'] = path['date']
        tempPage['iso_date'] = path['iso_date']
        tempPage['title'] = title
        tempPage['pageContent'] = pageContent

        fullContent.append(tempPage)

    return fullContent


# Copy assets to production folder
def move_assets(site_folder, path):
    assets = os.listdir(path)
    if assets:
        for asset in assets:
            asset = os.path.join(path, asset)
            if os.path.isfile(asset):
                shutil.copy(asset, site_folder+path)
    else:
        print("No assets found!")


# Transforms the file locations to an array of strings
def clean_path(path):
    path = re.sub('\.md$', '', path)
    items = path.split('/')
    path_items = {}
    path_items["slug"] = path + ".html"
    path_items["folder"] = items[0]
    path_items["file"] = items[1]

    if path_items["file"] == "index":
        path_items["parent_url"] = ""
        path_items["parent_text"] = "l'accueil"
    else:
        path_items["parent_url"] = items[0]
        path_items["parent_text"] = items[0]

    path_items["date"] = items[1]

    # Converts the EU date to US date to allow page sorting
    if path_items["date"] != "index":
        path_items["iso_date"] = str(
            datetime.strptime(path_items["date"], '%d-%m-%Y'))
    else:
        # If index page, add a fake date to avoid empty object
        path_items["iso_date"] = str(
            datetime.strptime("01-01-2000", '%d-%m-%Y'))

    return path_items


# Generate the list of sub pages for each section
def generate_sub_pages(entries, num, folder, title):

    # Sort entries by date using the iso_date format
    entries.sort(key=lambda x: x["iso_date"], reverse=True)

    # Take n number of entries (5 for the home, all for the sub-section pages)
    selected_entries = entries[:num]

    # Create the list
    sub_page_list = "<ul class='listing'>"
    for entry in selected_entries:
        if title == True:
            link_url = entry["slug"]
        else:
            link_url = entry["file"] + ".html"

        if entry["file"] != "index":
            entryString = "<li><a href='" + \
                link_url + "'>" + entry["date"] + \
                " : " + entry["title"] + "</a></li>\n"
            sub_page_list = sub_page_list + entryString
    sub_page_list += "</ul>"

    # If a title is necessary, use the folder name
    if title == True:
        title = "<h2>" + folder.capitalize() + \
            "</h2>"
        sub_page_list = title + sub_page_list
        sub_page_link = "<small><a href='" + \
            build_url + folder + "'>Voir tout</a></small>"
        sub_page_list += sub_page_link

    return sub_page_list


# Creates the home page using home.md
def create_home_page(template, site_folder):

    # Read the file and add "content_list" as a future replacement point for sub page listing
    html = markdown(open("home.md", "r").read()) + "content_list"

    # Replace template strings with content
    template = template.replace('page_title', "Accueil")
    template = template.replace('page_body', html)
    template = template.replace('build_url', build_url)
    template = template.replace('page_navigation', "")

    return template


# Create RSS Feed
def create_rss_feed(rss_entries, rss_template, rss_item_template, site_folder):
    template = open(rss_template, 'r').read()
    itemTemplate = open(rss_item_template, 'r').read()
    rss_entries.sort(key=lambda x: x["iso_date"], reverse=True)

    rss_items = ""
    for rss_entry in rss_entries:
        entry_template = itemTemplate
        entry_template = entry_template.replace(
            'rssItemTitle', rss_entry["title"])
        entry_template = entry_template.replace('rssItemUrl', build_url +
                                                rss_entry["slug"])
        entry_template = entry_template.replace(
            'rssItemDate', rss_entry["iso_date"])
        entry_template = entry_template.replace(
            'rssItemContent', rss_entry["pageContent"])
        rss_items = rss_items + entry_template

    template = template.replace('site_name', config.site_name)
    template = template.replace('site_meta_description',
                                config.site_meta_description)
    template = template.replace('build_url', build_url)
    template = template.replace('date_build', str(
        datetime.now().date()))
    template = template.replace('rss_content', rss_items)

    rssFile = open(site_folder + "feed.xml", "w")
    rssFile.write(template)
    rssFile.close()
    return


def generate_website():
    print('Welcome to the builder!')

    # If build folder exists delete it
    if os.path.exists(config.build_folder):
        shutil.rmtree(config.build_folder)

    # Make new folders
    os.makedirs(config.build_folder + config.assets_folder)

    # Get main html template
    template = open(config.template_file, 'r').read()

    # Create home page
    home_page = create_home_page(template, config.build_folder)

    rss_entries = []

    for folder in config.content_folder:
        pages = glob.glob(folder + '**/*.md', recursive=True)
        entries = create_entries(pages)
        sub_pages_list = generate_sub_pages(
            entries, len(entries), folder, False)

        # For each section, create a short listing of sub pages and add it to the home page
        home_pageSubList = generate_sub_pages(entries, 5, folder, True)
        home_page = home_page.replace('content_list', home_pageSubList +
                                      "content_list")
        home_page = home_page.replace('page_date', "")

        generate_html_pages(config.build_folder, entries, template,
                            sub_pages_list, config.template_nav)

        for entry in entries:
            rss_entries.append(entry)

     # Move the assets
    move_assets(config.build_folder, config.assets_folder)

    # Once all sections have been processed, finish the home page
    # Removes the "content_list" in the partial
    home_page = home_page.replace('content_list', "")
    home_page = home_page.replace('site_name', config.site_name)
    home_page = home_page.replace('site_meta_description',
                                  config.site_meta_description)
    home_page = home_page.replace(
        'twitter_name', config.twitter_name)
    pageFile = open(config.build_folder + "index.html", "w")
    pageFile.write(home_page)
    pageFile.close()

    # Create RSS File
    create_rss_feed(rss_entries, config.rss_template,
                    config.rss_item_template, config.build_folder)


# Triggers the website build
generate_website()
