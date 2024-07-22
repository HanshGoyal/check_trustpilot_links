from flask import Flask, request, render_template, send_file, redirect
import requests
import bs4
import csv
import concurrent.futures

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

def process_link(link):
    correct_tag = 'data-service-review-date-time-ago'
    no_review_tag = 'styles_noReviewsTitle'

    try:
        # Get the HTML of the page
        res = requests.get(link)
        res.raise_for_status()
        soup = bs4.BeautifulSoup(res.text, 'html.parser')
        with open('data.txt', 'w') as f:
            f.write(soup.prettify())

        with open('data.txt', 'r') as file:
            html_content = file.read()

        # Find the index of correct_tag
        start_index_correct_tag = html_content.find(correct_tag)
        start_index_no_review_tag = html_content.find(no_review_tag)

        if start_index_correct_tag != -1:
            # Find the index of '>' after correct_tag
            start_index_correct_tag = html_content.find('>', start_index_correct_tag)

            # Find the index of '</p>' before '</div>'
            end_index_p = html_content.find('</p>', start_index_correct_tag)
            end_index_div = html_content.find('</div>', start_index_correct_tag)

            if end_index_p != -1 and end_index_p < end_index_div:
                return link, 'Deleted', 'Review Removed'
            else:
                # Find the index of '<' after the '>' found above
                end_index = html_content.find('<', start_index_correct_tag)

                if end_index != -1:
                    # Extract data between '>' and '<'
                    extracted_data = html_content[start_index_correct_tag + 1: end_index]
                    print_statement = extracted_data.strip()  # Remove leading/trailing whitespaces

                    # Return link and extracted data
                    return link, 'Live', print_statement
                else:
                    return link, 'Live', "Couldn't find closing tag '<' after correct_tag"
        elif start_index_no_review_tag != -1:
            return link, 'Deleted', 'No Review Found'
        else:
            return link, 'Error', "Couldn't find correct_tag"
    except requests.exceptions.HTTPError as err:
        if err.response.status_code == 404:
            return link, 'Deleted', '404error'
        else:
            return link, 'Error', str(err)
    except Exception as e:
        return link, 'Error', str(e)

@app.route('/process_links', methods=['POST'])
def process_links():
    links = request.form.get('links')
    with open('links.txt', 'w') as links_file:
        links_file.write(links)

    links_list = [link.strip() for link in links.split('\n') if link.strip()]

    results = []
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            future_to_link = {executor.submit(process_link, link): link for link in links_list}
            for future in concurrent.futures.as_completed(future_to_link):
                try:
                    result = future.result()
                    results.append(result)
                except Exception as exc:
                    link = future_to_link[future]
                    results.append((link, 'Error', str(exc)))

        # Write results to result.csv
        with open('result.csv', 'w') as result_file:
            result_file.write("Link,Status,Comment\n")
            for result in results:
                result_file.write(f"{result[0]},{result[1]},{result[2]}\n")

    except Exception as e:
        return str(e), 500  # Return error message if something goes wrong

    return redirect('/show_data')  # Redirect to show_data route

@app.route('/download_result')
def download_result():
    return send_file('result.csv', as_attachment=True)

@app.route('/show_data')
def show_data():
    with open('result.csv', 'r') as result_file:
        csv_reader = csv.reader(result_file)
        next(csv_reader)  # Skip header row
        data = list(csv_reader)

    live_count = 0
    deleted_count = 0

    for row in data:
        status = row[1].strip()  # Extract the status
        if status == "Live":
            live_count += 1
        elif status == "Deleted":
            deleted_count += 1

    return render_template('show_data.html', data=data, live_count=live_count, deleted_count=deleted_count)

if __name__ == '__main__':
    app.run(debug=True)
