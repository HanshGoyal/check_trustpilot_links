from flask import Flask, request, render_template, send_file, redirect
import requests
import bs4
import csv
import os

app = Flask(__name__)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/process_links', methods=['POST'])
def process_links():
    links = request.form.get('links')
    with open('links.txt', 'w') as links_file:
        links_file.write(links)
    try:
        correct_tag = 'data-service-review-date-time-ago'
        no_review_tag ='styles_noReviewsTitle'

        # Open result.csv to write the output
        with open('result.csv', 'w') as result_file:
            result_file.write("Link,Status,Comment\n")  # Write header

            for link in links.split('\n'):
                link = link.strip()  # Remove leading/trailing whitespaces
                if not link:
                    continue  # Skip empty lines in links.txt

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
                            result_file.write(f"{link},Deleted,Review Removed\n")
                        else:
                            # Find the index of '<' after the '>' found above
                            end_index = html_content.find('<', start_index_correct_tag)

                            if end_index != -1:
                                # Extract data between '>' and '<'
                                extracted_data = html_content[start_index_correct_tag + 1: end_index]
                                print_statement = extracted_data.strip()  # Remove leading/trailing whitespaces

                                # Write link and extracted data to result.csv
                                result_file.write(f"{link},Live,{print_statement}\n")
                            else:
                                result_file.write(f"{link},Live,Couldn't find closing tag '<' after correct_tag\n")
                    elif start_index_no_review_tag != -1:
                        result_file.write(f"{link},Deleted,No Review Found\n")
                    else:
                        result_file.write(f"{link},Error,Couldn't find correct_tag\n")
                except requests.exceptions.HTTPError as err:
                    if err.response.status_code == 404:
                        result_file.write(f"{link},Deleted,404error\n")
                    else:
                        raise  # Re-raise exception if it's not a 404 Client Error

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
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
