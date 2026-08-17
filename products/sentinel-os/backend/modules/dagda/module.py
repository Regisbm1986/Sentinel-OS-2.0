import requests

DAGDA_API_URL = "http://127.0.0.1:5000/v1"


def check_dagda_status():

    try:

        response = requests.get(
            f"{DAGDA_API_URL}/status",
            timeout=5
        )

        return response.status_code == 200

    except Exception:
        return False


def run_dagda(image_name):

    if not image_name:
        return {
            "status": "warning",
            "message": "Nenhuma imagem Docker especificada."
        }

    try:

        response = requests.post(
            f"{DAGDA_API_URL}/check/images/{image_name}",
            timeout=10
        )

        if response.status_code == 202:

            hist_response = requests.get(
                f"{DAGDA_API_URL}/history/{image_name}",
                timeout=5
            )

            if hist_response.status_code == 200:

                return {
                    "status": "success",
                    "message": "Análise concluída.",
                    "data": hist_response.json()
                }

            return {
                "status": "running",
                "message": "Análise em execução."
            }

        elif response.status_code == 404:

            return {
                "status": "error",
                "message": f"Imagem '{image_name}' não encontrada."
            }

        return {
            "status": "error",
            "message": response.text
        }

    except requests.exceptions.ConnectionError:

        return {
            "status": "error",
            "message": "Dagda Server offline."
        }

    except Exception as ex:

        return {
            "status": "error",
            "message": str(ex)
        }
