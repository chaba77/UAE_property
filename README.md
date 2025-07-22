# PropertyFinder UAE API

This is a Flask API that scrapes property data from PropertyFinder UAE.

## Project Structure

- `app.py`: Main Flask application that handles API requests
- `requirements.txt`: Python dependencies
- `render.yaml`: Configuration for Render deployment
- `Procfile`: Configuration for web servers

## Local Development

1. Install dependencies:
```
pip install -r requirements.txt
```

2. Run the application:
```
python app.py
```

3. The API will be available at `http://localhost:5000`

## API Usage

Send a POST request to `/scrape` with the following JSON body:

```json
{
  "main_location": "Dubai", 
  "option": "Rent",
  "property_type": "Apartment",
  "number_of_bedrooms": "2",
  "sub_location": "Dubai Marina"
}
```

## Deployment to Render

This project is configured for deployment on Render.com. Follow these steps:

1. Create a new Web Service on Render
2. Connect your repository
3. Use the following settings:
   - **Name**: propertyfinder-api (or your preferred name)
   - **Environment**: Python
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `gunicorn app:app --workers 2 --timeout 120`

Render will automatically use the `render.yaml` configuration in this repository.
