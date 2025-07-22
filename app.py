from flask import Flask, request, jsonify
import json
import requests
from urllib.parse import urlparse, parse_qs
from time import sleep

app = Flask(__name__)

# ---------- Mapping Dictionaries ----------

main_locations = {
    "Ajman": "5",
    "Umm Al Quwain": "2",
    "Al Ain": "8",
    "Abu Dhabi": "6",
    "Fujairah": "7",
    "Ras Al Khaimah": "3",
    "Dubai": "1",
    "Sharjah": "4"
}

options = {
    "Rent": "2",
    "Buy": "1",
    "Commercial rent": "4",
    "Commercial buy": "3",
    "New Projects": "5"
}

property_types = {
    "Apartment": "1",
    "Villa": "35",
    "Townhouse": "22",
    "Penthouse": "20",
    "Compound": "42",
    "Duplex": "24",
    "Full Floor": "18",
    "Half Floor": "29",
    "Whole Building": "10",
    "Land": "5",
    "Bulk Sale Unit": "30",
    "Bungalow": "31",
    "Hotel & Hotel Apartment": "45"
}

# ---------- Scraper Functions ----------

def fetch_property_data(page, params):
    url = "https://www.propertyfinder.ae/search/_next/data/OJefluvpw_53_FSTVIQCT/en/search.json"
    params["page"] = page

    headers = {
        "X-Nextjs-Data": "1",
        "Sec-Ch-Ua-Platform": "\"Linux\"",
        "Accept-Language": "en-US,en;q=0.9",
        "Sec-Ch-Ua": "\"Not)A;Brand\";v=\"8\", \"Chromium\";v=\"138\"",
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/138.0.0.0 Safari/537.36",
        "Sec-Ch-Ua-Mobile": "?0",
        "Accept": "*/*",
        "Referer": "https://www.propertyfinder.ae/en/search",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Dest": "empty",
    }

    response = requests.get(url, headers=headers, params=params)
    response.raise_for_status()
    return response.json()


def extract_clean_data(data):
    search_data = data["pageProps"]["searchResult"]
    listings_raw = search_data.get("listings", [])
    listings = []

    for item in listings_raw:
        prop = item.get("property")
        if not prop:
            continue

        location = prop.get("location", {})
        agent = prop.get("agent", {})
        broker = prop.get("broker", {})

        contact_email = None
        contact_phone = None
        for contact in prop.get("contact_options", []):
            if contact["type"] == "email":
                contact_email = contact["value"]
            if contact["type"] == "phone":
                contact_phone = contact["value"]

        listing = {
            "title": prop.get("title"),
            "description": prop.get("description"),
            "price": {
                "value": prop.get("price", {}).get("value"),
                "currency": prop.get("price", {}).get("currency")
            },
            "location": location.get("full_name"),
            "bedrooms": prop.get("bedrooms"),
            "bathrooms": prop.get("bathrooms"),
            "size_sqft": prop.get("size", {}).get("value"),
            "furnished": prop.get("furnished"),
            "completion_status": prop.get("completion_status"),
            "listed_date": prop.get("listed_date"),
            "image_url": prop.get("images", [{}])[0].get("medium"),
            "share_url": prop.get("share_url"),
            "amenities": prop.get("amenity_names", []),
            "agent": {
                "name": agent.get("name"),
                "email": contact_email,
                "phone": contact_phone,
                "languages": agent.get("languages")
            },
            "broker": {
                "name": broker.get("name"),
                "email": broker.get("email"),
                "phone": broker.get("phone")
            }
        }

        listings.append(listing)

    return {
        "meta": search_data.get("meta", {}),
        "results": listings
    }

# ---------- API Route ----------

@app.route("/scrape", methods=["POST"])
def scrape():
    try:
        body = request.get_json()

        # Read readable inputs
        location_name = body.get("main_location")
        option_name = body.get("option")
        type_name = body.get("property_type")
        bedrooms = body.get("number_of_bedrooms")
        sub_location = body.get("sub_location")

        # Validate
        if location_name not in main_locations:
            return jsonify({"error": f"Location '{location_name}' not found"}), 404
        if option_name not in options:
            return jsonify({"error": f"Option '{option_name}' not found"}), 404
        if type_name not in property_types:
            return jsonify({"error": f"Property type '{type_name}' not found"}), 404

        main_locationID = main_locations[location_name]
        optionID = options[option_name]
        property_typeID = property_types[type_name]

        base_params = {
            "l": main_locationID,
            "c": optionID,
            "t": property_typeID,
            "bdr[]": bedrooms,
            "fu": 0,
            "ob": "mr"
        }

        # Fetch main page
        page1_data = fetch_property_data(1, base_params)
        search_data = page1_data["pageProps"]["searchResult"]
        page_props = page1_data["pageProps"]
        meta = search_data.get("meta", {})
        aggregation_links = page_props.get("pageMeta", {}).get("aggregationLinks", [])

        params_to_use = base_params.copy()

        # Sub-location handling
        if sub_location and aggregation_links:
            match = next((link for link in aggregation_links if link["name"].lower() == sub_location.lower()), None)
            if match:
                parsed_link = urlparse(match["link"])
                sub_params_raw = parse_qs(parsed_link.query)
                sub_location_id = sub_params_raw.get("l", [None])[0]
                if sub_location_id:
                    params_to_use["l"] = sub_location_id

        # Fetch and aggregate up to 4 pages
        first_data = fetch_property_data(1, params_to_use)
        meta = first_data["pageProps"]["searchResult"].get("meta", {})
        page_count = meta.get("page_count", 1)
        pages_to_fetch = min(4, page_count)

        all_results = []
        first_page_results = extract_clean_data(first_data)
        all_results.extend(first_page_results["results"])

        for page in range(2, pages_to_fetch + 1):
            page_data = fetch_property_data(page, params_to_use)
            clean_data = extract_clean_data(page_data)
            all_results.extend(clean_data["results"])
            sleep(0.3)

        final_output = {
            "meta": meta,
            "total_listings": len(all_results),
            "results": all_results
        }

        return jsonify(final_output)

    except Exception as e:
        return jsonify({"error": str(e)}), 500


if __name__ == "__main__":
    # Use environment variable for port with fallback to 5000
    # This is necessary for Render deployment
    import os
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port, debug=(os.environ.get("FLASK_ENV") == "development"))
