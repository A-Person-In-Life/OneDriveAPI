from concurrent.futures import *
import os
import requests
from msal import PublicClientApplication, SerializableTokenCache
import webbrowser


class oneDriveApi:
    def __init__(self, tenantId, clientId, scopes, cache_path):
        self.tenantId = tenantId
        self.clientId = clientId
        self.scopes = scopes
        self.accessToken = None
        self.cache_path = cache_path
        
        authority = f"https://login.microsoftonline.com/{tenantId}"
        token_cache = SerializableTokenCache()
        with open(cache_path, "r") as f:
            token_cache.deserialize(f.read())
        self.app = PublicClientApplication(client_id=clientId,authority=authority,token_cache=token_cache)

        accounts = self.app.get_accounts()
        if accounts:
            result = self.app.acquire_token_silent(scopes, account=accounts[0])
        else:
            flow = self.app.initiate_device_flow(scopes=scopes)
            if "error" in flow:
                raise ValueError(f"Device flow error: {flow['error_description']}")
            print(flow["message"])
            webbrowser.open(flow["verification_uri"])
            result = self.app.acquire_token_by_device_flow(flow)

        if "access_token" in result:
            print("Access token acquired!")
            print(result["access_token"][:100] + "...")
            self.accessToken = result["access_token"]
        else:
            raise ValueError(f"Error acquiring token: {result.get('error_description')}")

        if token_cache.has_state_changed:
            with open(cache_path, "w") as f:
                f.write(token_cache.serialize())

    def downloadFile(self, file_path, local_destination):
        version = "v1.0"
        urlSafePath = requests.utils.quote(file_path)
        url = f"https://graph.microsoft.com/{version}/me/drive/root:/{urlSafePath}"
        headers = {"Authorization": f"Bearer {self.accessToken}"}

        response = requests.get(url, headers=headers)
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            download_url = data.get("@microsoft.graph.downloadUrl")
            filename = data.get("name")
            print(f"Download URL: {download_url}")
            file = requests.get(download_url)
            with open(os.path.join(local_destination,filename), "wb") as f:
                f.write(file.content)
            
        else:
            print(f"Response: {response.text}")
            return
        
    def uploadFile(self, onedriveFolder, localFilePath):
        pass


def differ(local_path, icloud_file):
    icloud_size = icloud_file.size
    local_size = os.path.getsize(local_path)

    if local_size != icloud_size:
        return True
    
    print(icloud_file.date_modified.timestamp())
    print(os.path.getmtime(local_path))

    if (os.path.getmtime(local_path) == icloud_file.date_modified.timestamp()):
        return True
    
    return False    

def upload_file(file_path, icloud_folder):
    with open(file_path, "rb") as f:
        icloud_folder.upload(f, filename=os.path.basename(file_path))


def push_icloud(local_folder_path, icloud_folder=None):
    print("Scanning local folder:")
    files = []

    for file in os.listdir(local_folder_path):
        if os.path.isfile(os.path.join(local_folder_path, file)):
            files.append(file)
    print(f"Found {len(files)} files to upload!")
    
    executer = ThreadPoolExecutor(max_workers=4)
    print("Created a pool of 4 threads!") 
    
    futures = []
    for file in files:
        print(f"Scheduling upload for {file}")
        future = executer.submit(upload_file, os.path.join(local_folder_path, file), icloud_folder)
        futures.append(future)
    
    for future in as_completed(futures):
        try:
            future.result()
        except Exception as e:
            print(f"An upload failed: {e}")
    
    executer.shutdown(wait=True)
    print("All uploads finished!")


if __name__ == "__main__":
    base_dir = "/home/gavin/downloads/icloud_api_config/"
    onedrive_auth = os.path.join(base_dir, "onedrive_auth.txt")
    onedriveAuthCache = os.path.join(base_dir, "onedrive_auth_cache.json")

    with open(onedrive_auth, "r") as f:
        clientId = f.readline().strip()
        tenantId = f.readline().strip()
        scopes = f.readline().strip().split(",")

    api = oneDriveApi(tenantId, clientId, scopes, onedriveAuthCache)
    api.uploadFile(r"onedrive_test",r"/home/gavin/downloads/onedrive_test/Test.docx")
