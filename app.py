import os
import requests
import xml.etree.ElementTree as ET
from flask import Flask, Response
from datetime import datetime, timedelta
import argparse
import pytz

app = Flask(__name__)

def get_f1_schedule():
    """Fetches the current F1 season schedule from the Jolpica API."""
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get("https://api.jolpi.ca/ergast/f1/2025.json", headers=headers)
        response.raise_for_status()  # Raise an exception for bad status codes
        return response.json()['MRData']['RaceTable']['Races']
    except requests.exceptions.RequestException as e:
        print(f"Error fetching F1 schedule: {e}")
        return None

def generate_xmltv(races, target_timezone):
    """Generates an XMLTV string from a list of F1 races, including all sessions and placeholders,
    converted to the specified target_timezone."""
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

    all_programmes = []

    for race in races:
        race_name = race['raceName']
        circuit_name = race['Circuit']['circuitName']
        locality = race['Circuit']['Location']['locality']
        country = race['Circuit']['Location']['country']

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
                "is_placeholder": False
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
                        "is_placeholder": False
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
                        "is_placeholder": True
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

    # Determine the next event for the channel display name
    next_event_name = "Formula 1" # Default if no events found
    if all_programmes:
        # Find the first actual session (not a placeholder)
        for p in all_programmes:
            if not p.get("is_placeholder", False):
                next_event_name = p["title"].replace("F1 ", "") # Remove "F1 " prefix
                break

    # Add a channel entry
    channel = ET.SubElement(tv, "channel")
    channel.set("id", "f1.channel")
    display_name = ET.SubElement(channel, "display-name")
    display_name.text = f"F1 TV - {next_event_name}"

    return ET.tostring(tv, encoding='unicode')

@app.route('/epg.xml')
def epg():
    """The main EPG endpoint."""
    races = get_f1_schedule()
    xml_data = generate_xmltv(races, app.config['TARGET_TIMEZONE'])
    return Response(xml_data, mimetype='application/xml')

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
