import sys
sys.path.insert(0, 'src')

from encryption_utils import decrypt_data

# Test decrypting one of the encrypted values
encrypted = "gAAAAABpGrBaEV1zwC0Yojw3JdyTOW4J_7gH0E_CTbrz9vh7Mi_40zM1eYrLGWwmLDjk46jQQrLWGgTvbdC30Vgi6ale0hfoJw=="

try:
    decrypted = decrypt_data(encrypted)
    print(f"Successfully decrypted: {decrypted}")
except Exception as e:
    print(f"Decryption failed: {e}")
    print(f"Error type: {type(e)}")
