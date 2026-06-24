import requests
import os


class Utils:

    @staticmethod
    def download_image(image_url: str) -> str:

        project_root = os.getcwd()

        file_name = image_url.split("/")[-1].split("?")[0]
        file_path = os.path.join(project_root, file_name)

        response = requests.get(image_url)
        if response.status_code == 200:
            with open(file_path, "wb") as image_file:
                image_file.write(response.content)
            return file_path
        else:
            raise Exception(
                f"Failed to download image: {image_url}, status code: {response.status_code}"
            )

    @staticmethod
    def delete_image(file_path: str) -> None:

        if os.path.exists(file_path):
            os.remove(file_path)
        else:
            print(f"File not found: {file_path}")
