# import json
# import os
# # from openai import OpenAI

# # client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

# def map_form_fields(labels, profile_data):

#     prompt = f"""
#     You are an intelligent job application assistant.

#     Match each form label to the most appropriate value
#     from the profile JSON.

#     Form Labels:
#     {labels}

#     Profile Data:
#     {profile_data}

#     Return ONLY valid JSON in this format:
#     {{
#         "label_text": "value_from_profile"
#     }}
#     """

#     response = client.chat.completions.create(
#         model="gpt-4o-mini",
#         messages=[{"role": "user", "content": prompt}],
#         temperature=0.2
#     )

#     content = response.choices[0].message.content

#     return json.loads(content)

def map_form_fields(form_fields: list, user_data: dict):
    mapped_data = {}

    for field in form_fields:
        field_lower = field.lower()

        if "name" in field_lower:
            mapped_data[field] = user_data.get("full_name")

        elif "email" in field_lower:
            mapped_data[field] = user_data.get("email")

        elif "phone" in field_lower:
            mapped_data[field] = user_data.get("phone")

        elif "location" in field_lower:
            mapped_data[field] = user_data.get("location")

        elif "experience" in field_lower:
            mapped_data[field] = user_data.get("experience_years")

        else:
            mapped_data[field] = ""

    return mapped_data
