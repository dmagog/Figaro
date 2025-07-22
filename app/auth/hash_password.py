from passlib.context import CryptContext

# Создаем контекст с использованием bcrypt алгоритма
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class HashPassword:
    """
    Класс для хеширования и верификации паролей с использованием bcrypt.
    """
    
    def create_hash(self, password: str) -> str:
        """
        Создает хеш из переданного пароля.

        Args:
            password (str): Пароль для хеширования

        Returns:
            str: Хешированный пароль
        """
        return pwd_context.hash(password)
    
    def verify_hash(self, plain_password: str, hashed_password: str) -> bool:
        """
        Проверяет соответствие пароля его хешу.

        Args:
            plain_password (str): Пароль в открытом виде
            hashed_password (str): Хешированный пароль для сравнения

        Returns:
            bool: True если пароль соответствует хешу, False в противном случае
        """
        return pwd_context.verify(plain_password, hashed_password)