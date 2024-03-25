from selenium import webdriver
from selenium.webdriver.common.by import By
import time
import miro_config
import datetime
import requests
import json
import csv
from jira import JIRA
import sd_prod_creds

# #miro_config contains:
# login_url = 'https://miro.com/login/'
# email
# password 
# org_id

#sd_prod_creds
# url = 'https://servicedesk.domain_name.com/'
# token 

b = webdriver.Chrome()
b.implicitly_wait(30)

b.get(miro_config.login_url)

email = b.find_element(By.ID, 'email')
email.send_keys(miro_config.email)

#logging in..
print('Loggin in to Miro..')
button = b.find_element(By.CLASS_NAME, 'btn-primary')
try:
    password = b.find_element(By.ID, 'password')
    password.send_keys(miro_config.password)

    button.click()
    time.sleep(5)
except(Exception):
    button.click()

    password = b.find_element(By.ID, 'password')
    password.send_keys(miro_config.password)
    try:
        rejectCookie = b.find_element(By.ID, 'onetrust-reject-all-handler')
        rejectCookie.click()
        
        button.click()
    except(Exception):
        button.click()
    time.sleep(5)

# getting cookies from selenium session
cookies_dict = {}
for cookie in b.get_cookies():
    cookies_dict[cookie['name']] = cookie['value']

print('Go to the users section...')
users_url = f'https://miro.com/app/settings/company/{miro_config.org_id}/users'
b.get(users_url)
b.maximize_window()

# pull the list of guest users who was inactive for more than 30 days
one_month_ago_date = datetime.date.today() - datetime.timedelta(days=31)
inactive_users_api_url = f'https://miro.com/api/v1/organizations/{miro_config.org_id}/members?deactivated=false&fields=id%2Cpicture%7Bsize44%2Csize210%7D%2Cemail%2Ctype%2Cname%2ClastActiveDate%2Crole%2CdayPassesActivatedInLast30Days%2Clicense%2CaccountsNumber%2CaddingDate&roles=ORGANIZATION_EXTERNAL_USER&accountRoles=ADMIN%2CUSER&lastActiveDateEnd={one_month_ago_date}T00%3A00%3A00.000Z&sort=name&limit=400&offset=0'
print('Getting inactive users...')
r = requests.get(inactive_users_api_url, cookies=cookies_dict, verify=False)

inactive_guests_count = json.loads(r.text)['size']
print(f'{inactive_guests_count} inactive guest users are detected...')

users_list = json.loads(r.text)['data']

print('Starting deleting inactive users...')
while True:
    #setting filters
    filter_button = b.find_element(By.CLASS_NAME, 'button__icon-BZb5S').click()

    role_checkboxes = b.find_elements(By.CLASS_NAME, 'checkbox-bchAW')
    guest_checkbox = role_checkboxes[2].click()
    activity_buttons = b.find_elements(By.CLASS_NAME, 'radiobutton__wrap')
    inactive_radiobutton = activity_buttons[2].click()

    #click to search line to hide filters pop-up
    search_line = b.find_element(By.ID, 'search-id').click()
    time.sleep(2)
    if len(b.find_elements(By.XPATH, '//*[@id="layer-scroll-ref"]/div[2]/main/div/div/div[4]/table/tbody/tr')) > 1: #while the table of users is not empty     
        # select bulk operaation to delete 50 users
        bulk_checkboxes = b.find_elements(By.CLASS_NAME, 'checkbox-bchAW')
        bulk_checkbox = bulk_checkboxes[0].click()
        bulk_actions = b.find_element(By.CLASS_NAME, 'rtb-select--primary').click()
        
        #deliting users
        delete_button = b.find_element(By.CSS_SELECTOR, 'div[data-testid="select-dropdown_item_4"] > button[data-testid="active-users__delete-from-org-button"]').click()
        confirm_button = b.find_element(By.CSS_SELECTOR, 'button[data-testid="delete-users-without-teams-modal__delete-button"]').click()
        time.sleep(20)

        b.refresh()

        time.sleep(5)
    else:
        break

print('Deletion is completed.')
b.quit()

#create .csv file
current_date = datetime.date.today()
csv_file = open(f'C:\\Miro_deleted_users\miro_inactive_guest_users_{current_date}.csv', 'w', encoding='utf-8', newline='') 
writer = csv.writer(csv_file, dialect='excel')
writer.writerow(["Id", "Name", "addingDate", "email", "lastActiveDate"]) # write headers to .csv file

print('Writing users to .csv file...')
for user in users_list:
    #print(user)
    name = user['name']
    id = user['id']
    adding_date = user['addingDate']
    user_email = user['email']
    if 'lastActiveDate' in user:
        last_active_date = user['lastActiveDate']
    else:
        last_active_date = None

    writer.writerow([id, name, adding_date, user_email, last_active_date])

csv_file.close()
print('Export to .csv file is completed...')

#connecting to SD Jira
print('Connecting to Jira...')
jiraOptions = {'server' : sd_prod_creds.url
               }
jira = JIRA(server=jiraOptions, token_auth=sd_prod_creds.token)

#looking for current SD ticket
jql = 'assignee = currentUser() and summary ~ \'Miro Licence Monitoring\' and resolution = Unresolved'
issue = jira.search_issues(jql_str=jql)[0]
print(f'SD ticket number is {issue.key}')

#open generated csv file in binary mode
file = open(f'C:\\Miro_deleted_users\miro_inactive_guest_users_{current_date}.csv', 'rb')

print('Attaching the file to the ticket...')
jira.add_attachment(issue, file)

file.close()

#required fields to resolve SD request
fields = {
    'customfield_10790': {
        'value': 'Administrative'
    },
    'customfield_10003': {
        'value': 'LP',
        'child': {
            'value': 'Access Control'
        }
    },
    'labels': ['miro']
}

print('Resolving the ticket...')
jira.transition_issue(issue, 'Resolve', fields, 'Inactive guest users are deleted. List of users attached.', '20')