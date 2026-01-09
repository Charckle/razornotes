import secrets

secret_key = secrets.token_hex(32)
print("Generated secret key:", secret_key)
print("\nAdd this to your .env file:")
print(f"RKKV_SECRET_KEY={secret_key}")
