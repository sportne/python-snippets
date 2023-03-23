from atlassian import Confluence
import re
        
def get_confluence_client():
    """
    Returns an instance of the Confluence client with the server URL and API token
    obtained from environment variables.
    """
    url = os.environ.get('CONFLUENCE_URL')
    token = os.environ.get('CONFLUENCE_TOKEN')
    username = os.environ.get('CONFLUENCE_USERNAME')
    return Confluence(url=url, username=username, password=token)
    
def get_table_data(page_title: str, heading_text: str):
    """
    Retrieves the table data from the Confluence page with the specified title and heading.

    Args:
        page_title (str): The title of the Confluence page containing the table.
        heading_text (str): The text of the heading that comes before the table.

    Returns:
        List[Dict[str, Any]]: A list of dictionaries representing the rows in the table.
    """
    confluence = get_confluence_client()
    page_data = confluence.get_page_by_title(space='MY_SPACE', title=page_title, expand='body.storage', representation='wiki')
    heading_match = re.search(fr"(^|\n)h[1-6]\. {re.escape(heading_text)}\s*\n", page_data['body']['storage']['value'])
    if not heading_match:
        return None
    table_match = re.search(r'\|\s*(.*?)\s*\|\|.*?\n((?:\|\s*.*?\s*\|\|.*?\n)+)', page_data['body']['storage']['value'][heading_match.end():], re.DOTALL)
    if not table_match:
        return None
    headers = [header.strip() for header in table_match.group(1).split('|') if header.strip()]
    rows = [dict(zip(headers, [value.strip() for value in row.split('|') if value.strip()])) for row in table_match.group(2).split('\n') if row.strip()]
    return rows

    
def update_confluence_table(space: str, page_title: str, heading_text: str, update_fn: Callable[[dict], dict]):
    """
    Update a table on a Confluence page.

    Parameters:
    space (str): The space key of the Confluence space where the page is located.
    page_title (str): The title of the page containing the table.
    heading_text (str): The heading text that comes before the table.
    update_fn (Callable[[dict], dict]): A function that takes a dictionary representing a row in the table as input,
        modifies it as needed, and returns the modified dictionary.

    Returns:
    None
    """
    # Retrieve the page content using the get_page_by_title method
    page_data = confluence.get_page_by_title(space=space, title=page_title, expand='body.storage', representation='wiki')

    # Search for the heading text using regular expressions
    heading_match = re.search(r'(^|\n)h[1-6]\. {}\s*\n'.format(re.escape(heading_text)), page_data['body']['storage']['value'])
    if heading_match:
        # Search for the table after the heading using regular expressions
        table_match = re.search(r'\|\s*(.*?)\s*\|\|.*?\n((?:\|\s*.*?\s*\|\|.*?\n)+)', page_data['body']['storage']['value'][heading_match.end():], re.DOTALL)
        if table_match:
            headers = [header.strip() for header in table_match.group(1).split('|') if header.strip()]
            rows = [dict(zip(headers, [value.strip() for value in row.split('|') if value.strip()] )) for row in table_match.group(2).split('\n') if row.strip()]

            # Apply the update function to each row in the table
            for row in rows:
                updated_row = update_fn(row)
                row.update(updated_row)

            # Convert the list of dictionaries back into Wiki markup format
            table_markup = '||{}||\n{}'.format(
                '||'.join(headers),
                '\n'.join(['|{}|'.format('|'.join([row.get(header, '') for header in headers])) for row in rows])
            )

            # Update the page content with the modified table data
            # This command is quite involved so here's some more context
            # page_data['body']['storage']['value']: This retrieves the current value of the body.storage.value field of the page_data dictionary. This field contains the page content in Wiki markup format.
            # [:heading_match.end()]: This slices the page content up to the end of the heading that precedes the table. This ensures that any content that comes before the table is preserved, while any content that comes after the table is removed.
            # +: This concatenates the sliced content with the modified table data.
            # re.sub(r'\|\s*(.*?)\s*\|\|.*?\n((?:\|\s*.*?\s*\|\|.*?\n)+)', table_markup, page_data['body']['storage']['value'][heading_match.end():], 1, re.DOTALL): This replaces the table data in the page content with the modified table data using a regular expression substitution. Here's what each part of the regular expression means:
            ## \|\s*(.*?)\s*\|\|: This matches the header row of the table in Wiki markup format. The .*? inside the parentheses captures the text of each header cell.
            ## .*?\n: This matches the separator row of the table in Wiki markup format.
            ## ((?:\|\s*.*?\s*\|\|.*?\n)+): This matches one or more rows of the table in Wiki markup format. The (?:...) syntax creates a non-capturing group that matches a single row of the table. The | inside the group matches the cell separator. The .*? matches the text of each cell. The + outside the group matches one or more rows.
            # The re.DOTALL flag at the end of the regular expression causes the . character to match any character, including newlines.
            # The table_markup argument to re.sub is the modified table data, which will replace the matched table data in the page content.
            # The 1 argument to re.sub tells the method to perform at most one substitution. This ensures that only the first occurrence of the table is modified, even if there are multiple tables on the page.
            page_data['body']['storage']['value'] = page_data['body']['storage']['value'][:heading_match.end()] + re.sub(r'\|\s*(.*?)\s*\|\|.*?\n((?:\|\s*.*?\s*\|\|.*?\n)+)', table_markup, page_data['body']['storage']['value'][heading_match.end():], 1, re.DOTALL)
            confluence.update_page_by_id(page_data['id'], data=page_data)
            
def main():
    # Set up Confluence client
    confluence = get_confluence_client()

    # Get data from Confluence table
    page_title = "My Confluence Page"
    heading_text = "My Table Heading"
    table_data = get_table_data(page_title, heading_text)

    # Update the table data
    def update_fn(row: Dict[str, Any]) -> Dict[str, Any]:
        row["Status"] = "Completed"
        return row

    update_confluence_table("MY_SPACE", page_title, heading_text, update_fn)

if __name__ == "__main__":
    main()