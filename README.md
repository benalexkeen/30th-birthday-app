# README

As this was designed as a single use application, it's not the most parameterised but feel free to butcher it and use it for your own tasks as you want.

## Running Locally

First you'll need to stand up a Cosmos DB instance in Azure with a database with a Mongo API.

Within this CosmosDB database, you'll need to create a database named "app_db" and collection named "attendees".

Then add a single document in the format:
```
{
    "_id" : 1,
    "first_name" : "Ben",
    "last_name" : "Keen",
    "group_id" : 1,
    "email_address" : "benalexkeen@gmail.com",
    "rsvp" : 0,
    "dietary_reqs" : "",
    "invite_sent" : "",
    "invited_by" : "Ben Keen"
}
```

To send out email invites, you'll also need to set up a sendgrid API key and an email address to use as your "from_email".

To show the Google Map, you'll need to have a google maps API key.

Now create a file named `config.json` and add the following contents:
```
{
  "flask_key": "<flask_key>",
  "cosmos_username": "<cosmos_username>",
  "cosmos_password": "<cosmos_password>",
  "cosmos_db_name": "<cosmos_db_name>",
  "sendgrid_api_key": "<sendgrid_api_key>",
  "google_maps_key": "<google_maps_api_key>",
  "from_email": "<from_email>"
}
```

You'll then need to create a virtual environment and install the requirements:
```sh
pip install -r requirements.txt
```

To create an admin user, run:

```sh
python admin.py
```

Then you can run:

```sh
python app.py
```

And the application should run at http://localhost:5000

You can add attendees from the admin panel by navigating to http://localhost:5000/admin


## Deploymemt to Azure

To deploy to Azure, use the following commands:
```sh
# Login to Azure account.
az login

# Create a resource group.
az group create --location uksouth --name <rg-name>

# Create an App Service plan (change SKU to FREE for free tier).
az appservice plan create --name <app-service-plan-name> --resource-group  <rg-name> --sku P1V2 --location uksouth --is-linux

az webapp up --name <web-app-name> --plan <app-service-plan-name> --resource-group  <rg-name> --location uksouth
```
