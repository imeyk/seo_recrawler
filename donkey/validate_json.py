import json

def validate_json(json_data):
    try:
        json.loads(json_data)
        return True
    except ValueError:
        return False

def validate_json2(json_string):
    try:
        json_data = json.loads(json_string)
        
        # Проверка структуры JSON
        required_keys = [
            "type", "project_id", "private_key_id", "private_key",
            "client_email", "client_id", "auth_uri", "token_uri",
            "auth_provider_x509_cert_url", "client_x509_cert_url",
            "universe_domain"
        ]
        
        for key in required_keys:
            if key not in json_data:
                return False, f"Отсутствует обязательный ключ: {key}"
        
        # Дополнительные проверки
        if json_data["type"] != "service_account":
            return False, "Неверный тип аккаунта"
        
        # Другие проверки, если необходимо
        
        return True, "Валидный JSON"
    
    except json.JSONDecodeError:
        return False, "Неверный формат JSON"
    
    except Exception as e:
        return False, f"Произошла ошибка: {str(e)}"