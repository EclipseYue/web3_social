from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa, padding
from cryptography.hazmat.primitives.serialization import load_pem_private_key, load_pem_public_key
from cryptography.exceptions import InvalidKey
import base64

class ChatRoomCrypto:
    def __init__(self):
        self.padding = padding.OAEP(
            mgf=padding.MGF1(algorithm=hashes.SHA256()),
            algorithm=hashes.SHA256(),
            label=None
        )

    def generate_room_keypair(self):
        """生成新的RSA密钥对"""
        try:
            # 生成私钥
            private_key = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048
            )
            
            # 获取公钥
            public_key = private_key.public_key()
            
            # 序列化私钥
            private_pem = private_key.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            
            # 序列化公钥
            public_pem = public_key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )
            
            return {
                'private_key': private_pem.decode('utf-8'),
                'public_key': public_pem.decode('utf-8')
            }
        except Exception as e:
            print(f"生成密钥对时出错: {str(e)}")
            return None

    def encrypt_message(self, message, public_key_pem):
        """使用公钥加密消息"""
        try:
            if not message or not public_key_pem:
                print("消息或公钥为空")
                return None
                
            # 加载公钥
            public_key = load_pem_public_key(public_key_pem.encode('utf-8'))
            
            # 加密消息
            encrypted = public_key.encrypt(
                message.encode('utf-8'),
                self.padding
            )
            
            # 返回Base64编码的加密数据
            return base64.b64encode(encrypted).decode('utf-8')
            
        except Exception as e:
            print(f"加密消息时出错: {str(e)}")
            return None

    def decrypt_message(self, encrypted_data_str, private_key_pem):
        """使用私钥解密消息"""
        try:
            if not encrypted_data_str or not private_key_pem:
                print("加密数据或私钥为空")
                return None
                
            # 加载私钥
            private_key = load_pem_private_key(
                private_key_pem.encode('utf-8'),
                password=None
            )
            
            # 解码Base64数据
            encrypted_data = base64.b64decode(encrypted_data_str.encode('utf-8'))
            
            # 解密消息
            decrypted = private_key.decrypt(
                encrypted_data,
                self.padding
            )
            
            return decrypted.decode('utf-8')
            
        except Exception as e:
            print(f"解密消息时出错: {str(e)}")
            return None 