import requests
import hashlib
import json

# Username and password is found on the incoice from the heating company
username="<username>"
password="<password>"
# The supplier ID is found on eforsyning.dk
# In the browser press F12 and look at the network traffic.
# Find a line like this one:
#    GetVaerkSettings?forsyningid=<some-identifier 8+4+4+4+12 characters)>
supplierid="<supplier id>"
# The official domain for the service:
serverurl="https://eforsyning.dk"

####
# This section can be filled out with values found from running the program once.
# It will save some API calls to annotate these values to here.
# Yes - they could go to a config file dumped by the program but I am lazy, and this is
# only to show it can be done,

# These ids can be found by setting them to "" and getting the data from running the program.
# It saves some API calls to just hardcode them whem known.  It is my guess most provate consumers
# only have a single meter, so this is what is assumed here.
asset_id="1"
installation_id="1"
# The API server is fetched by asking eforsyning where it is.
api_server = "https://api2.dff-edb.dk/smoerum/"

# Half-way internal variables.  You can put the crypt_id here to save an API call while playing
# with the code. It seems the token is good for about an hour or so.
crypt_id = "" 

# Just for demonstration purposes.  The examples hardcode the year.
year_mark = ""

# Selectros for the examples to run. A LOT of data comes out!
dump_response = False
show_yearly_data = True
show_monthly_data = True
show_daily_data = True

if api_server == "":
    ## Get the URL to the REST API service ##
    # From where does the supplerid some?
    settingsURL="/umbraco/dff/dffapi/GetVaerkSettings?forsyningid="
    result = requests.get(serverurl + settingsURL + supplierid)
    #print(result.json())
    result_dict = json.loads(result.text)
    # Got the API server, given the supplier ID.
    api_server = result_dict['AppServerUri']
    #print(api_server)

if crypt_id == "":
    # With the API server URL we can authenticate and get a token:
    security_token_url = "system/getsecuritytoken/project/app/consumer/"
    result = requests.get(api_server + security_token_url + username)
    #print(result.json())
    # Returns: {'Token': 'b75832af1278160b201121632289d2fa'}
    result_dict = json.loads(result.text)
    token = result_dict['Token']
    hashed_password = hashlib.md5(password.encode()).hexdigest();
    crypt_string = hashed_password + token
    crypt_id = hashlib.md5(crypt_string.encode()).hexdigest()
    print(f"crypt ID       : {crypt_id}")

    # Use the new token to login to the API service
    auth_url = "system/login/project/app/consumer/"+username+"/installation/1/id/"

    result = requests.get(api_server + auth_url + crypt_id)
    result_dict = json.loads(result.text)
    if result_dict['Result'] == 1:
        print("Login success\n")
    else:
        print("Login failed. Bye.\n")
        exit(1)

# We are authenticated, now get some data
result = requests.get(api_server + "api/getebrugerinfo?id=" + crypt_id)
#print(result.json())
result_dict = json.loads(result.text)
euser_id = str(result_dict['id'])

# Find the asset ID and installation ID if not specified at the top
if asset_id == "":
    post_find_installations_url = "api/FindInstallationer?id=" + crypt_id
    data = {"Soegetekst": "",
            "Skip": "0",
            "Take": "10000",
            "EBrugerId": euser_id,
            "Huskeliste": "null",
            "MedtagTilknyttede": "false"
           }

    # Returns:
    #  {"Installationer":
    #        [
    #         {"EjendomNr":<username>,
    #          "Adresse":"<your address>",
    #          "InstallationNr":1,  <- this value is needed
    #          "ForbrugerNr":"<username>",
    #          "MålerNr":"<metering device serial>",
    #          "By":"<your town>",
    #          "PostNr":"<your post code>",
    #          "AktivNr":1, <- this calue is needed
    #          "Målertype":"sharky batteri sen føler"
    #         }
    #        ]
    #   }
    result = requests.post(api_server + post_find_installations_url, data=json.dumps(data))
    result_dict = json.loads(result.text)
    asset_id = str(result_dict['Installationer'][0]['AktivNr'])
    installation_id = str(result_dict['Installationer'][0]['InstallationNr'])
    print(f"Asset Id       : {asset_id}")
    print(f"Installation Id: {installation_id}")

# Show one way to fetch the current year we are in from the API service.
# Obviously one could also just use a calendar lookup...
# It seems the web application uses this record to set date ranges on queries.
if year_mark == "":
    # Get the current year data record
    get_current_year_mark_url="api/getaktuelaarsmaerke?id=" + crypt_id + "&unr=" + username + "&anr=" + asset_id + "&inr=" + installation_id
    result = requests.get(api_server + get_current_year_mark_url)
    # Returns:
    #   {
    #     "aarsmaerke": 2020,
    #     "aarsmaerke_slut": "31-12-2020",
    #     "aarsmaerke_start": "01-01-2020"
    #   }
    #print(json.dumps(result.json(), indent=2, sort_keys=True))
    result_dict = json.loads(result.text)
    print(f"Year      : {result_dict['aarsmaerke']}")
    print(f"Year Start: {result_dict['aarsmaerke_start']}")
    print(f"Year End  : {result_dict['aarsmaerke_slut']}\n")
    year_mark=result_dict['aarsmaerke']

def retrieve_meter_data(year = "0", month = False, day = False, from_date = "0", to_date = "0", include_expected_reading = True, dump = False):
    # URL for retrieving metering data - this is the main endpoint to manipulate
    # It is a POST operation, and the data package is different depending on what is wanted back.
    #
    # Date format: DD-MM-YYYY

    post_meter_data_url = "api/getforbrug?id="+crypt_id+"&unr="+username+"&anr="+asset_id+"&inr="+installation_id # POST

    include_data_in_between = "false"
    if month or day:
        include_data_in_between = "true"

    data_filter = "afMaanedsvis"
    data_average = "false"
    if day:
        data_filter = "afDagsvis"
        data_average = "true"

    data_exp_read = "false"
    if include_expected_reading:
        data_exp_read = "true"

    data = {
#            "aCallKey":"0", ##
            "Ejendomnr":username,
            "AktivNr":asset_id,
            "I_Nr":installation_id,
            "AarsMaerke":year,
            "ForbrugsAfgraensning_FraDato":from_date,
            "ForbrugsAfgraensning_TilDato":to_date,
            "ForbrugsAfgraensning_FraAflaesning":"0",
            "ForbrugsAfgraensning_TilAflaesning":"2",

#            "ForbrugsAfgraensning_FraMellNr":"0",
#            "ForbrugsAfgraensning_TilMellnr":"0",

#            "ForbrugsAfgraensning_FraAfl_nr":"0",
#            "ForbrugsAfgraensning_TilAfl_nr":"0",

#            "ForbrugsAfgraensning_TilJournalNr":"0",
            "ForbrugsAfgraensning_MedtagMellemliggendeMellemaflas":include_data_in_between, ## true || false

            "Optioner":"foBestemtBeboer, foSkabDetaljer, foMedtagWebAflaes",
            "AHoejDetail":"false", ## true || false

            "Aflaesningsfilter":data_filter, ## afMaanedsvis || afDagsvis || afUfiltreret
            "AflaesningsFilterDag":"ULTIMO",
            "AflaesningsUdjaevning":data_average, ## true || false (Create interpolated data it seems)

            "SletFiltreredeAflaesninger":"true", ## true || false (Get rid of filtered data?)
            "MedForventetForbrug":data_exp_read, ## true || false (Include or exclude expected reading values)
            "OmregnForbrugTilAktuelleEnhed":"true" # true || false
#            "BestemtEnhed":"0",
#            "Godkendelser":"0",
#            "RadEksponent2":"0",
#            "RadEksponent1":"0",
#            "Belastningsfaktor":"0",
           }

    result = requests.post(api_server + post_meter_data_url, data=json.dumps(data))
    if dump:
        print(json.dumps(result.json(), indent=2, sort_keys=True))
    return json.loads(result.text)


def stof(fstr):
  """Convert string with ',' string float to float"""
  return float(fstr.replace(',', '.'))

def prettyprint_energy_data(data):
    text  = f"Periode: {data['AarStart']} - {data['AarSlut']}\n"
    text += f"------------------------------------------------------"
    print(text)
    for fl in data['ForbrugsLinjer']['TForbrugsLinje']:
        data = dict()
        data['temperature'] = {}

        text =  (
                 f"Periode: {fl['FraDatoStr']} - {fl['TilDatoStr']}\n"
                 f"------------------------------------------------------\n"
                 f"Afkøling          | Frem     | Retur    | Fv.Retur | Afkøling\n"
                 f"                  |    {stof(fl['Tempfrem']):>4.2f} |   {stof(fl['TempRetur']):>4.2f}  | {stof(fl['Forv_Retur']):>4.2f}    | {stof(fl['Afkoling']):>4.2f}\n\n"
                 f"Måler             | Start     | Slut      | Forbrug  | Fv.Forbrug | Fv. aflæsning\n"
                )

        for reading in fl['TForbrugsTaellevaerk']:
            unit = reading['Enhed_Txt']
            text += f"{reading['IndexNavn']:>5} [{unit:>9}] | {stof(reading['Start']):>9.3f} | {stof(reading['Slut']):>9.3f} | {stof(reading['Forbrug']):>8.3f} |"
            if reading['IndexNavn'] == "ENG1":
                text += f"  {stof(fl['ForventetForbrugENG1']):>9.3f} |     {stof(fl['ForventetAflaesningENG1']):>9.3f}\n"
            elif reading['IndexNavn'] == "M3":
                text += f"  {stof(fl['ForventetForbrugM3']):>9.3f} |     {stof(fl['ForventetAflaesningM3']):>9.3f}\n"
            else:
                text += "\n"
        print(text)

def print_example_header(header):
  print("#######################################################")
  print(f"##### {header:38} #####")
  print("#######################################################")

# Get yearly energy use
if not show_yearly_data:
    print_example_header(" Yearly data")
    # Try and get yearly data
    data = retrieve_meter_data(year = "2019", dump=dump_response)
    prettyprint_energy_data(data)
    data = retrieve_meter_data(year = "2020", dump=dump_response)
    prettyprint_energy_data(data)

if show_monthly_data:
    print_example_header("Monthly Data full year")
    # Monthly data for a full year:
    data = retrieve_meter_data(year="2020", month = True, dump=dump_response)
    prettyprint_energy_data(data)

    print_example_header("Monthly data, quarter")
    # Monthly data for a quarter (not really limited because the API ignores date ranges):
    data = retrieve_meter_data(year="2020", month = True, from_date="01-01-2020", to_date="31-12-2020", dump=dump_response)
    prettyprint_energy_data(data)

if show_daily_data:
    # Daily data for a week (not really limited because the API ignores date ranges):
    # It looks at the year and returns data from the full year.
    print_example_header(" Daily data one week")
    data = retrieve_meter_data(year="2020", day = True, from_date="01-12-2020", to_date="07-12-2020", dump=dump_response)
    prettyprint_energy_data(data)

# Other URLs
get_prognose_url="api/getberegnregnskab"
get_meter_reading_url="api/GetAflaesOpl"
