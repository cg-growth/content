def get_response(endpoint, headers, params, URL):

    url = "".join((URL, endpoint))
    response = rq.get(url, headers=headers, params=params)

    try:
        data = response.json()
    except ValueError:
        print("Invalid JSON response")
        return None

    if response.status_code != 200:
        print(f"Failed to fetch data, status code {response.status_code}")

    return data
