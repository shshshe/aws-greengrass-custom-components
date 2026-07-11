"""
Copyright 2020 Amazon.com, Inc. or its affiliates. All Rights Reserved.
Last Updated on 25th Feb, 2023
Authored by: Shashi Shekhar
Reviewed by: Reetesh varshney
Updated on 11rth July, 2026 to replace database connection variables with secret manager parameters.
"""

import mysql.connector
import logging
import random
import uuid
import time
import calendar
import datetime
import json
import boto3

logger = logging.getLogger()

"""
#Create the secret in AWS Secrets Manager with a structure like:
json
{
  "username": "your_db_user",
  "password": "your_db_password"
}

#Ensure IAM permissions: The AWS credentials running this script need permissions to access Secrets Manager:
json
{
  "Effect": "Allow",
  "Action": "secretsmanager:GetSecretValue",
  "Resource": "arn:aws:secretsmanager:region:account:secret:historian-db-credentials*"
}
"""

# AWS Secrets Manager configuration
SECRET_NAME = "historian-db-credentials"  # Update with your actual secret name
AWS_REGION = "us-east-1"  # Update with your AWS region

# Database configuration
db_host_name = "<Enter Host name or IP address of the Historian DB>"
db_name = "<Database name>"

def get_db_credentials_from_secrets_manager():
    """
    Retrieve database credentials from AWS Secrets Manager.
    
    Returns:
        tuple: (db_user, db_password)
    """
    try:
        # Create Secrets Manager client
        secrets_client = boto3.client('secretsmanager', region_name=AWS_REGION)
        
        # Retrieve the secret
        response = secrets_client.get_secret_value(SecretId=SECRET_NAME)
        
        # Parse the secret value
        if 'SecretString' in response:
            secret = json.loads(response['SecretString'])
            db_user = secret.get('username')
            db_password = secret.get('password')
            
            if not db_user or not db_password:
                raise ValueError("Secret does not contain 'username' or 'password' keys")
            
            logger.info("Successfully retrieved database credentials from Secrets Manager")
            return db_user, db_password
        else:
            raise ValueError("Secret does not contain SecretString")
            
    except Exception as error:
        logger.error(f"Error retrieving credentials from Secrets Manager: {error}")
        raise


# Retrieve credentials from Secrets Manager
db_user, db_password = get_db_credentials_from_secrets_manager()

# Create the connection object
myconn = mysql.connector.connect(
    host=db_host_name, user=db_user, passwd=db_password, database=db_name)

# creating the cursor object
cur = myconn.cursor()

# Example: "/ER/297/Generator/Temperature"
property_alias = "<sitewise measurement property alias>"
temperature = 0.0000000
quality = 'UNCERTAIN'

# This method creates simulated historian record to be read by custom component


def insertIntoHistorian(uid):

    # historian data are intialized as global variables
    global temperature
    global quality
    global property_alias
    global myconn
    global cur

    ct = datetime.datetime.now()
    ts = ct.timestamp()

    # create record into ER_297_GENERATOR historian table
    insert_stmt = (
        "INSERT INTO ER_297_GENERATOR (ASSET_VALUE, PROPERTY_ALIAS, DATA_QUALITY, ID, DATE_TIME) VALUES (%s, %s, %s, %s, %s);")
    data = (temperature, property_alias, quality, uid, ct)

    try:
        cur.execute(insert_stmt, data)
        myconn.commit()
        print("Data insertion committed")
    except Exception as error:
        print(error)
        print(type(error))
        print("Data insertion rolledback")
        myconn.rollback()

# This methiod creates random measurement value to be inserted into Historian table


def getValues():
    global temperature
    global quality
    try:
        temperature = random.uniform(20, 25)  # nosec
        quality = 'GOOD'

        seed = random.uniform(1, 10)  # nosec
        logger.info("seed: {}".format(seed))
        logger.info("temperature: {}".format(temperature))

        if seed == 3 or seed == 6:
            temperature = random.uniform(35, 45)  # nosec
            quality = 'BAD'
        elif seed == 7:
            temperature = random.uniform(25, 35)  # nosec
            quality = 'UNCERTAIN'

        temperature = float(temperature)
        logger.info("temperature: {}".format(temperature))

        print(temperature)
        print(quality)

    except Exception as error:
        logger.error("error during random temperature generation: %s", error)

# To maintain a balance between number of records inserted and streamed to sitewise, data older than 8 hours will be deleted.


def deleteOlderRecord():
    global myconn
    global cur

    delete_stmt = (
        "DELETE FROM ER_297_GENERATOR WHERE DATE_TIME < now() - interval 480 MINUTE;")

    try:
        cur.execute(delete_stmt)
        myconn.commit()
        print("Data delete committed")
    except Exception as error:
        print(error)
        print(type(error))
        print("Data delete rolledback")
        myconn.rollback()


def main():
    global myconn
    while True:
        deleteOlderRecord()
        uid = str(uuid.uuid4())
        getValues()
        insertIntoHistorian(uid)
        time.sleep(2)
    myconn.close()


main()
