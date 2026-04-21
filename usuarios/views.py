from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework import status
from rest_framework.authtoken.models import Token
from rest_framework.permissions import AllowAny
from datetime import datetime
from drf_spectacular.utils import extend_schema, OpenApiExample


class LoginView(APIView):
    permission_classes = [AllowAny]

    @extend_schema(
        summary="Iniciar sesión",
        description="Autentica al usuario mediante email y password. Retorna el token necesario para consumir la API protegida.",
        examples=[
            OpenApiExample(
                "Login correcto",
                value={
                    "email": "juan@correo.com",
                    "password": "123456"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Respuesta exitosa",
                value={
                    "token": "abc123token..."
                },
                response_only=True,
            ),
        ],
    )

    def post(self, request):

        email = request.data.get("email")
        password = request.data.get("password")

        try:
            user_obj = User.objects.get(email=email)
            username = user_obj.username
        except User.DoesNotExist:
            return Response(
                {"error": "Credenciales incorrectas"},
                status=status.HTTP_401_UNAUTHORIZED
            )

        user = authenticate(username=username, password=password)

        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({"token": token.key})

        return Response(
            {"error": "Credenciales incorrectas"},
            status=status.HTTP_401_UNAUTHORIZED
        )

class RegisterView(APIView):
    permission_classes = [AllowAny]
    @extend_schema(
        summary="Registrar usuario",
        description="Crea un nuevo usuario en el sistema. El email será usado como username para el login.",
        examples=[
            OpenApiExample(
                "Registro de usuario",
                value={
                    "email": "juan@correo.com",
                    "password": "123456",
                    "first_name": "Juan",
                    "last_name": "Serna"
                },
                request_only=True,
            ),
            OpenApiExample(
                "Respuesta exitosa",
                value={
                    "message": "Usuario creado correctamente"
                },
                response_only=True,
            ),
        ],
    )

    def post(self, request):

        email = request.data.get("email")
        password = request.data.get("password")
        first_name = request.data.get("first_name")
        last_name = request.data.get("last_name")

        if not email or not password:
            return Response(
                {"error": "Email y password son requeridos"},
                status=status.HTTP_400_BAD_REQUEST
            )

        if User.objects.filter(email=email).exists():
            return Response(
                {"error": "El correo ya está registrado"},
                status=status.HTTP_400_BAD_REQUEST
            )

        user = User.objects.create_user(
            username=email,  # <- truco importante
            email=email,
            password=password,
            first_name=first_name,
            last_name=last_name
        )

        return Response(
            {"message": "Usuario creado correctamente"},
            status=status.HTTP_201_CREATED
        )