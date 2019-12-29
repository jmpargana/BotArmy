from datetime import datetime, timedelta
from random import randint
from bs4 import BeautifulSoup as bs

import random
import json
import string
import hashlib
import sqlite3
import uuid
import sys
import io
import requests as req


GIVEN_NAMES = "https://en.wikipedia.org/wiki/List_of_most_popular_given_names"
SURNAMES = "https://en.wikipedia.org/wiki/List_of_most_common_surnames_in_Europe"
GOOGLE_API = "https://accounts.google.com/signup/v2/webcreateaccount?flowName=GlifWebSignIn&flowEntry=SignUp"
DATABASE = "BotArmy"
TABLE = """
CREATE TABLE users (
    username TEXT,
    salt TEXT,
    hashed_password TEXT
)"""


def get_names():
    """ Perform a get requests to the wikipedia pages containing
        all needed data for the most popular given and surnames 
        and save the results in a JSON file

    """

    # requests for both wikipedia articles
    given_names_soup = bs(req.get(GIVEN_NAMES).text, "html.parser")
    surnames_soup = bs(req.get(SURNAMES).text, "html.parser")

    # parse given names page and save in a dictionary
    given_names = {
        country[0].string: [
            name.string
            for name in country[1:]
            if name.string[0] != "[" and name.string[0].isupper()
        ]
        for country in [
            table.find_all("a") for table in given_names_soup.find_all("tr")
        ]
        if len(country) > 2
    }

    surnames = {
        h2.span.string: [
            a.string
            for a in h2.find_next_sibling("table").select("td>a")
            if a and a.string[0].isupper()
        ]
        for h2 in surnames_soup.find_all("h2")[:-4]
        if h2.span
    }

    # parse surnames page and save in a dictionary
    with io.open("names.json", "w", encoding="utf8") as json_file:
        json.dump(
            {"given_names": given_names, "surnames": surnames},
            json_file,
            ensure_ascii=False,
            indent=4,
        )


def create_bots(amount):
    """ Using the newly created names.json file containing a list
        of the most popular given and surnames in the worls
        perform API requests to google's sign up page 

    """

    cursor = establish_connection(DATABASE, TABLE)

    with open("bots.json", "w") as json_file:
        for i in amount:
            # search for the right combination and generate a random date
            given_name, surname = name_selector()
            birthday = birthday_generator()
            username, cursor = create_account(given_name, surname, birthday, cursor)

            # save the results in a new json file
            if res.status_code == 200:
                json.dump(
                    {username: {"names": (given_name, surname), "birthday": birthday}},
                    json_file,
                )


def name_selector():
    """ Select a random name combination from the names.json file
        created earlier and try to match the country for the combination

    Return:
        the tuple

    """

    with io.open("names.json", "r", "utf8") as json_file:
        data = json.load(json_file)
        given_name = random.choice(data["given_names"])
        surname = random.choice(data["surnames"])

    return "_".join(given_name.split()), "_".join(surname.split())


def create_account(given_name, surname, birthdate, cursor):
    """ Fill the GOOGLE API form with the given data and store the result
        in a json file with a hashed password

    Params:
        given_name
        surname
        birthdate

    """

    # create user with typical mail format
    mail = given_name + "_" + surname + birthdate[:4]
    password = generate_password()

    # load the google page
    soup = bs(req.get(GOOGLE_API).text, "html.parser")
    soup.find_element_by_id('firstName').send_keys(given_name)
    soup.find_element_by_id('lasName').send_keys(surname)
    soup.find_element_by_id('passwd').select('input').send_keys(password)
    soup.find_element_by_id('confirm-passwd').select('input').send_keys(password)


    # submit form request

    # save values if request status was ok
    salt = uuid.uuid4().hex
    hashed_password = hashlib.sh512((salt + password).encode("UTF-8")).hexdigest()
    cursor = store_user(mail, salt, hashed_password, cursor)
    return mail, cursor


def establish_connection(database, table):
    """ Connect to a given database name and create a table entry
    
    Params:
        database name
        table definition declared in beggining of file

    Return:
        cursor on database

    """

    connection = sqlite3.connect(database)
    cursor = connection.cursor()
    cursor.execute(table)
    return cursor


def store_user(username, salt, hashed_password, cursor):
    """ Given the cursor and user values insert them to database

    Params:
        username
        salt used for hashing algorithm
        hashed_password
        cursor with current database position

    Return:
        cursor on database

    """

    add = "INSERT INTO users VALUES ('{}', '{}', '{}')"
    cursor.execute(add.format(username, salt, hashed_password))
    return cursor


def generate_password(size=16):
    """ Generate a random password of a given size with alphnumerical
        and special characters

    Params:
        size is the length of the password

    Return:
        the resulting password
    """
    chars = string.ascii_letters + string.digits + string.punctuation
    return "".join(random.choice(chars) for i in range(size))


def birthday_generator(maximum_age=99, date_format="%Y-%m-%d", repeat=1):
    """ Generates a date of bith in the specified format and range

    Params:
        maximum_age: the age relative to the current date
        date_format: format of the date in Python datetime.strftime format
        repeat: number of dates to generate
    Return:
        formatted date of birth
    """
    for _ in range(repeat):
        yield (
            datetime.today() - timedelta(days=randint(0, 365 * maximum_age))
        ).strftime(date_format)


def get_user(username, cursor):
    """ Might become different depending on how password are stored
    """

    row = cursor.execute(
        f"SELECT salt, hashed_password FROM users WHERE username = {username}"
    )
    salt, hashed_password = row


def main():
    """ Deal with command line arguments
        Create a n-amount of bots

    Params:
        sys.argv[1] amount of bots to be created

    """

    # user_amount = sys.argv[1]
    get_names()
    # create_bots(user_amount)


if __name__ == "__main__":
    main()
