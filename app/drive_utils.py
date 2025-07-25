import os
import io
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload, MediaFileUpload
from google.auth.transport.requests import Request

# Scopes para lectura y escritura (subida y descarga)
SCOPES = ['https://www.googleapis.com/auth/drive']

CREDENTIALS_PATH = 'config/credentials.json'
TOKEN_PATH = 'config/token.json'
FOLDER_ID = '1cn1qwr00h24aWQ7n0lCVb5RC-hPoYYra'


def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PATH, SCOPES)
    # Refrescar token si es necesario
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(CREDENTIALS_PATH, SCOPES)
            creds = flow.run_local_server(port=0)  # abre navegador para login
        with open(TOKEN_PATH, 'w') as token:
            token.write(creds.to_json())
    service = build('drive', 'v3', credentials=creds)
    return service

def listar_bases_de_datos(service):
    query = f"'{FOLDER_ID}' in parents and name contains '.db' and mimeType != 'application/vnd.google-apps.folder'"
    results = service.files().list(
        q=query,
        spaces='drive',
        fields="files(id, name)",
        pageSize=100
    ).execute()
    print("Respuesta Drive API:", results)  # <--- para debug
    return results.get('files', [])


def descargar_db(service, file_id, destino_local):
    request = service.files().get_media(fileId=file_id)
    fh = io.FileIO(destino_local, 'wb')
    downloader = MediaIoBaseDownload(fh, request)
    done = False
    while not done:
        status, done = downloader.next_chunk()
    print(f'✅ Archivo descargado: {destino_local}')

def subir_db_a_drive(service, local_path, nombre_archivo):
    file_metadata = {
        'name': nombre_archivo,
        'parents': [FOLDER_ID]  # <- Esto hace que el archivo vaya a la carpeta correcta
    }
    media = MediaFileUpload(local_path, mimetype='application/octet-stream')
    file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
    print(f'✅ Archivo subido a Drive con ID: {file.get("id")}')
    return file.get('id')


def subir_o_actualizar_db(service, local_path, nombre_archivo):
    query = f"name = '{nombre_archivo}' and '{FOLDER_ID}' in parents"
    results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
    files = results.get('files', [])
    media = MediaFileUpload(local_path, mimetype='application/octet-stream')
    
    if files:
        file_id = files[0]['id']
        updated_file = service.files().update(fileId=file_id, media_body=media).execute()
        print(f'✅ Archivo actualizado en Drive (ID: {file_id})')
        return file_id
    else:
        file_metadata = {'name': nombre_archivo, 'parents': [FOLDER_ID]}
        file = service.files().create(body=file_metadata, media_body=media, fields='id').execute()
        print(f'✅ Archivo subido a Drive con ID: {file.get("id")}')
        return file.get('id')

