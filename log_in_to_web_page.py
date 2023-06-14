from selenium import webdriver

from selenium.webdriver.common.by import By

def login(url, username, password):
    b = webdriver.Firefox() #open browser

    b.get(url)  #go to the page

    b.implicitly_wait(20) #sleep

    login_input = b.find_element('xpath', '//*[@id="i0116"]') #xpath of the email input box / could be any attribute such as css selector, class name etc.
    login_input.send_keys(username) #email input

    nextButton = b.find_element(By.CSS_SELECTOR, '#idSIButton9') #find the button usin css selector
    nextButton.click() 

    b.implicitly_wait(20)

    pass_input = b.find_element(By.CSS_SELECTOR, '#passwordInput') #find password input box 
    pass_input.send_keys(password) #password input

    signin_button = b.find_element(By.CSS_SELECTOR, '#submitButton') 
    signin_button.click()

login('https://login.microsoftonline.com', 'SBotalov@luxoft.com', 'Kbdthgekmxtvgbjy23!')