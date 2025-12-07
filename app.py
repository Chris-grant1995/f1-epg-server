import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response, send_file, request
from datetime import datetime, timedelta
import argparse
import pytz
from PIL import Image, ImageDraw, ImageFont
import io
import base64

app = Flask(__name__)

# Cache for downloaded images to avoid repeated downloads
image_cache = {}

app = Flask(__name__)

def get_f1_schedule():
    """Fetches the current F1 season schedule from the Jolpica API, with a fallback to next year."""
    current_year = datetime.now().year
    
    def fetch_schedule(year):
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
            response = requests.get(f"https://api.jolpi.ca/ergast/f1/{year}.json", headers=headers)
            response.raise_for_status()  # Raise an exception for bad status codes
            data = response.json()
            if data['MRData']['RaceTable']['Races']:
                return data['MRData']['RaceTable']['Races']
            return None
        except requests.exceptions.RequestException as e:
            print(f"Error fetching F1 schedule for {year}: {e}")
            return None

    # Try fetching the current year's schedule first
    races = fetch_schedule(current_year)
    
    # If the current year's schedule is empty, try the next year
    if not races:
        print(f"No races found for {current_year}, trying {current_year + 1}...")
        races = fetch_schedule(current_year + 1)
        
    return races

def generate_xmltv(races, target_timezone, base_url):
    """Generates an XMLTV string from a list of F1 races, including all sessions and placeholders,
    converted to the specified target_timezone, with F1 logo and country flags."""
    tv = ET.Element("tv")
    tv.set("generator-info-name", "F1 EPG Server")

    if not races:
        return ET.tostring(tv, encoding='unicode')

    # Define session types and their default durations
    session_types = {
        "FirstPractice": {"name": "First Practice", "duration_hours": 1},
        "SecondPractice": {"name": "Second Practice", "duration_hours": 1},
        "ThirdPractice": {"name": "Third Practice", "duration_hours": 1},
        "Qualifying": {"name": "Qualifying", "duration_hours": 1},
        "SprintQualifying": {"name": "Sprint Qualifying", "duration_hours": 0.5}, # 30 minutes
        "Sprint": {"name": "Sprint Race", "duration_hours": 1},
        "Race": {"name": "Race", "duration_hours": 2},
    }

    # Mapping from country name (from Ergast API) to ISO 3166-1 alpha-2 code for flagcdn.com
    country_code_map = {
        "Bahrain": "bh", "Australia": "au", "China": "cn", "Japan": "jp", "Saudi Arabia": "sa",
        "United States": "us", "Mexico": "mx", "Brazil": "br", "Canada": "ca", "Austria": "at",
        "Great Britain": "gb", "Hungary": "hu", "Belgium": "be", "Netherlands": "nl", "Italy": "it",
        "Singapore": "sg", "Azerbaijan": "az", "Qatar": "qa", "Abu Dhabi": "ae", "Spain": "es",
        "Monaco": "mc", "France": "fr", "Portugal": "pt", "Germany": "de", "Russia": "ru",
        "Turkey": "tr", "Malaysia": "my", "India": "in", "Korea": "kr", "Vietnam": "vn",
        "UAE": "ae", # Added United Arab Emirates
        "Europe": "eu", # For generic European events if any
        # Added more common F1 countries and reordered for clarity
    }

    all_programmes = []

    for race in races:
        race_name = race['raceName']
        circuit_name = race['Circuit']['circuitName']
        locality = race['Circuit']['Location']['locality']
        country = race['Circuit']['Location']['country']
        print(race)
        country_code = country_code_map.get(country, "gb") # Default to GB if not found

        sessions_for_weekend = []

        # Add the main Race session
        race_date_str = race['date']
        race_time_str = race.get('time', '00:00:00Z')
        try:
            start_time_utc = datetime.strptime(f"{race_date_str}T{race_time_str}", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
            end_time_utc = start_time_utc + timedelta(hours=session_types["Race"]["duration_hours"])
            sessions_for_weekend.append({
                "start": start_time_utc,
                "end": end_time_utc,
                "title": f"F1 {session_types['Race']['name']} - {race_name}",
                "desc": f"Live coverage of the Formula 1 {session_types['Race']['name']} for the {race_name} from {circuit_name} in {locality}, {country}.",
                "is_placeholder": False,
                "country_code": country_code
            })
        except ValueError as e:
            print(f"Error parsing date/time for main Race of '{race_name}': {e}")

        # Add other sessions
        for session_key, session_info in session_types.items():
            if session_key == "Race": # Already processed
                continue
            if session_key in race:
                session_date_str = race[session_key]['date']
                session_time_str = race[session_key].get('time', '00:00:00Z')

                try:
                    start_time_utc = datetime.strptime(f"{session_date_str}T{session_time_str}", "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=pytz.utc)
                    end_time_utc = start_time_utc + timedelta(hours=session_info["duration_hours"])
                    sessions_for_weekend.append({
                        "start": start_time_utc,
                        "end": end_time_utc,
                        "title": f"F1 {session_info['name']} - {race_name}",
                        "desc": f"Live coverage of the Formula 1 {session_info['name']} for the {race_name} from {circuit_name} in {locality}, {country}.",
                        "is_placeholder": False,
                        "country_code": country_code
                    })
                except ValueError as e:
                    print(f"Error parsing date/time for {session_info['name']} of '{race_name}': {e}")

        # Sort sessions for the weekend by start time
        sessions_for_weekend.sort(key=lambda x: x["start"])

        # Add placeholders between sessions
        for i in range(len(sessions_for_weekend)):
            current_session = sessions_for_weekend[i]
            all_programmes.append(current_session)

            if i < len(sessions_for_weekend) - 1:
                next_session = sessions_for_weekend[i+1]
                gap_start = current_session["end"]
                gap_end = next_session["start"]

                # Only add a placeholder if there's a significant gap (e.g., more than 5 minutes)
                if gap_end > gap_start + timedelta(minutes=5):
                    all_programmes.append({
                        "start": gap_start,
                        "end": gap_end,
                        "title": f"Next: {next_session['title'].replace('F1 ', '')} at {next_session['start'].astimezone(target_timezone).strftime('%H:%M %Z')}",
                        "desc": f"Waiting for the next Formula 1 session: {next_session['title'].replace('F1 ', '')}.",
                        "is_placeholder": True,
                        "country_code": None # Placeholders don't have a specific country flag
                    })

    # Sort all programmes (sessions and placeholders) by start time
    all_programmes.sort(key=lambda x: x["start"])

    # Generate XMLTV elements from the sorted programmes
    for p in all_programmes:
        programme = ET.SubElement(tv, "programme")
        # Convert to target timezone before formatting
        start_local = p["start"].astimezone(target_timezone)
        stop_local = p["end"].astimezone(target_timezone)

        programme.set("start", start_local.strftime("%Y%m%d%H%M%S %z"))
        programme.set("stop", stop_local.strftime("%Y%m%d%H%M%S %z"))
        programme.set("channel", "f1.channel")

        title = ET.SubElement(programme, "title")
        title.text = p["title"]

        desc = ET.SubElement(programme, "desc")
        desc.text = p["desc"]

        # Add country flag icon for actual sessions
        if not p.get("is_placeholder", False) and p.get("country_code"):
            icon = ET.SubElement(programme, "icon")
            icon.set("src", f"https://flagcdn.com/16x12/{p['country_code'].lower()}.png")


    # Determine the next event for the channel display name and icon
    next_event_name = "Formula 1" # Default if no events found
    next_event_country_code = "gb" # Initialize with a default country code
    current_utc_time = datetime.utcnow().replace(tzinfo=pytz.utc)

    if all_programmes:
        # Find the first actual session (not a placeholder) that starts after the current time
        found_next_event = False
        for p in all_programmes:
            if not p.get("is_placeholder", False) and p["start"] > current_utc_time:
                next_event_name = p["title"].replace("F1 ", "") # Remove "F1 " prefix
                next_event_country_code = p.get("country_code", "gb") # Get country code from the actual session
                print(f"DEBUG: Next event country code from programme: {p.get('country_code')}, mapped code: {next_event_country_code}") # Debug print
                found_next_event = True
                break
        
        # If no future events are found, set a "No upcoming races" message
        if not found_next_event:
            next_event_name = "No upcoming races"
            next_event_country_code = "gb" # Default to a generic country code

    # Add a channel entry
    channel = ET.SubElement(tv, "channel")
    channel.set("id", "f1.channel")
    display_name = ET.SubElement(channel, "display-name")
    display_name.text = f"F1 TV - {next_event_name}"
    # Always add F1 logo to the channel
    f1_logo_icon = ET.SubElement(channel, "icon")
    icon_url = f"{base_url}/channel_icon.png"
    if next_event_name != "No upcoming races":
        icon_url += f"?country_code={next_event_country_code.lower()}"
    f1_logo_icon.set("src", icon_url)

    return ET.tostring(tv, encoding='unicode')

@app.route('/epg.xml')
def epg():
    """The main EPG endpoint."""
    races = get_f1_schedule()
    # Get the base URL for generating absolute icon URLs
    base_url = request.url_root.rstrip('/') # e.g., http://localhost:5001
    xml_data = generate_xmltv(races, app.config['TARGET_TIMEZONE'], base_url)
    return Response(xml_data, mimetype='application/xml')

F1_LOGO_URL = "https://www.formula1.com/etc/designs/fom-website/images/f1_logo.png"
FLAG_BASE_URL = "https://flagcdn.com/w160/" # Higher resolution flags

# A simple mapping of country codes to representative background colors (hex codes)
# These are just examples and can be customized
COUNTRY_COLORS = {
    "bh": "#DC0000", # Bahrain Red
    "au": "#00008B", # Australia Dark Blue
    "cn": "#EE1C25", # China Red
    "jp": "#BC002D", # Japan Red
    "sa": "#006C35", # Saudi Arabia Green
    "us": "#B22234", # United States Red
    "mx": "#006847", # Mexico Green
    "br": "#009739", # Brazil Green
    "ca": "#D82B1F", # Canada Red
    "at": "#ED2939", # Austria Red
    "gb": "#00247D", # Great Britain Blue
    "hu": "#436F4D", # Hungary Green
    "be": "#FDDA24", # Belgium Yellow
    "nl": "#AE1C28", # Netherlands Red
    "it": "#008C45", # Italy Green
    "sg": "#EE2436", # Singapore Red
    "az": "#0098C1", # Azerbaijan Blue
    "qa": "#8A0046", # Qatar Maroon
    "ae": "#00732F", # UAE Green
    "es": "#AA151B", # Spain Red
    "mc": "#CE1126", # Monaco Red
    "fr": "#002395", # France Blue
    "pt": "#006600", # Portugal Green
    "de": "#000000", # Germany Black
    "ru": "#D52B1E", # Russia Red
    "tr": "#E30A17", # Turkey Red
    "my": "#00008B", # Malaysia Dark Blue
    "in": "#FF9933", # India Saffron
    "kr": "#00007D", # Korea Dark Blue
    "vn": "#DA251D", # Vietnam Red
    "eu": "#003399", # Europe Blue
    # Add more as needed
}

@app.route('/channel_icon.png')
def channel_icon():
    country_code = request.args.get('country_code')
    
    # Check cache first
    cache_key = f"channel_icon_{country_code or 'no_country'}"
    if cache_key in image_cache:
        return send_file(io.BytesIO(image_cache[cache_key]), mimetype='image/png')

    try:
        # Determine background color
        bg_color_hex = COUNTRY_COLORS.get(country_code, "#000000") if country_code else "#000000" # Default to black
        # Convert hex to RGB
        bg_color_rgb = tuple(int(bg_color_hex.lstrip('#')[i:i+2], 16) for i in (0, 2, 4))

        # Download F1 logo
        f1_logo_response = requests.get(F1_LOGO_URL)
        f1_logo_response.raise_for_status()
        f1_logo_img = Image.open(io.BytesIO(f1_logo_response.content)).convert("RGBA")

        # Download country flag only if a country_code is provided
        flag_img = None
        if country_code:
            try:
                flag_url = f"{FLAG_BASE_URL}{country_code}.png"
                flag_response = requests.get(flag_url)
                flag_response.raise_for_status()
                flag_img = Image.open(io.BytesIO(flag_response.content)).convert("RGBA")
            except requests.exceptions.RequestException as e:
                print(f"Could not download flag for {country_code}: {e}")

        # Define output image size
        output_width = 200
        output_height = 100
        combined_img = Image.new("RGBA", (output_width, output_height), bg_color_rgb + (255,)) # Opaque background

        # Define padding
        padding = 5

        # Resize F1 logo (e.g., 40% of output height, maintain aspect ratio)
        f1_logo_height = int(output_height * 0.4)
        f1_logo_width = int(f1_logo_img.width * (f1_logo_height / f1_logo_img.height))
        f1_logo_img = f1_logo_img.resize((f1_logo_width, f1_logo_height), Image.LANCZOS)
        
        # Create a new transparent image for the content
        content_height = f1_logo_height + (int(output_height * 0.3) + padding if flag_img else 0)
        content_img = Image.new("RGBA", (output_width, content_height), (0,0,0,0))

        # Paste F1 logo onto the content image
        f1_logo_x = (output_width - f1_logo_width) // 2
        f1_logo_y_in_content = 0 if flag_img else (content_height - f1_logo_height) // 2
        content_img.paste(f1_logo_img, (f1_logo_x, f1_logo_y_in_content), f1_logo_img)

        # Paste flag below the F1 logo if it exists
        if flag_img:
            flag_height = int(output_height * 0.3)
            flag_width = int(flag_img.width * (flag_height / flag_img.height))
            flag_img = flag_img.resize((flag_width, flag_height), Image.LANCZOS)
            flag_x = (output_width - flag_width) // 2
            flag_y = f1_logo_height + padding
            content_img.paste(flag_img, (flag_x, flag_y), flag_img)

        # Calculate position to paste the content image onto the background for vertical centering
        paste_y = (output_height - content_height) // 2
        
        # Paste the content image onto the background
        combined_img.paste(content_img, (0, paste_y), content_img)

        # Save to BytesIO object
        img_byte_arr = io.BytesIO()
        combined_img.save(img_byte_arr, format='PNG')
        img_byte_arr = img_byte_arr.getvalue()

        # Cache the image
        image_cache[cache_key] = img_byte_arr

        return send_file(io.BytesIO(img_byte_arr), mimetype='image/png')

    except requests.exceptions.RequestException as e:
        print(f"Error downloading image: {e}")
        # Fallback to a default image or error image
        return Response("Error generating icon", status=500)
    except Exception as e:
        print(f"Error processing image: {e}")
        return Response("Error generating icon", status=500)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description="F1 EPG Server")
    parser.add_argument('--port', type=int, default=5001,
                        help='Port to run the Flask server on (default: 5001)')
    parser.add_argument('--timezone', type=str, default='America/New_York',
                        help='Timezone for EPG output (e.g., Europe/London, America/New_York). Default: America/New_York')
    parser.add_argument('--host', type=str, default='0.0.0.0',
                        help='Host to run the Flask server on (default: 0.0.0.0)')
    args = parser.parse_args()

    try:
        app.config['TARGET_TIMEZONE'] = pytz.timezone(args.timezone)
    except pytz.exceptions.UnknownTimeZoneError:
        print(f"Error: Unknown timezone '{args.timezone}'. Defaulting to UTC.")
        app.config['TARGET_TIMEZONE'] = pytz.utc

    app.run(host=args.host, port=args.port)
