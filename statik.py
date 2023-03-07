# Author : Nemuel Wainaina
# Script to automate Static Malware Analysis

import binary2strings as b2s
import filetype
import hashlib
import json
import os
import requests
import sys
import urllib.request

from colorama import init, Fore

def print_header(title):
    title = "[*] " + title
    print(f"{BLUE} {title} {RESET}")
    print("{} {} {}".format(BLUE, '-'*len(title), RESET))

def print_info(name, info):
    print("{} {} {}: {}".format(YELLOW, name, RESET, info))

def has_internet_access():
    try:
        urllib.request.urlopen("https://google.com")
        return True
    except:
        return False
    
def load_config():
    with open("config", "r") as f:
        content = f.read()
    config = json.loads(content)
    return config['api_url'], config['api_key']

class VTScan:

    def __init__(self, sample, api_url, api_key) -> None:
        self.headers = {
            "x-apikey": api_key,
            "User-Agent": "Statik v.1.0.0",
            "Accept-Encoding": "gzip,deflate"
        }
        self.sample = sample
        self.api_url = api_url

    def analyze(self):
        if has_internet_access():
            self.files = {
                "file": (
                    os.path.basename(self.sample),
                    open(os.path.abspath(self.sample) , "rb")
                )
            }
            self.res = requests.post(self.api_url+"files", headers=self.headers, files=self.files)
            if self.res.status_code == 200:
                result = self.res.json()
                file_id = result.get("data").get("id")
            self.perform_analysis(file_id)
        else:
            print("{} [!]{} Can't reach VirusTotal (No internet connection)".format(RED, RESET))

    def display_malicious_findings(self, results):
        for r, _ in results:
            if results[r].get("category") == "malicious":
                print("="*25)
                print_info("Engine name", results[r].get("engine_name"))
                print_info("Engine version", results[r].get("engine_version"))
                print_info("Category", results[r].get("category"))
                print_info("Result", results[r].get("result"))
                print_info("Method", results[r].get("method"))
                print_info("Update", results[r].get("engine_update"))
                print("="*25)

    def perform_analysis(self, file_id):
        analysis_url = self.api_url + "analyses/" + file_id
        res = requests.post(analysis_url, headers=self.headers)
        if res.status_code == 200:
            result = res.json()
            status = result.get("data").get("attributes").get("status")
            if status == "completed":
                stats = result.get("data").get("attributes").get("stats")
                malicious = str(stats.get("malicious"))
                undetected = str(stats.get("undetected"))
                print_info("Malicious", malicious)
                print_info("Undetected", undetected)
                results = result.get("data").get("attributes").get("results")
                self.display_malicious_findings(results)                
            elif status == "queued":
                with open(os.path.abspath(self.sample), "rb") as f:
                    sample_hash = hashlib.sha256(f.read()).hexdigest()
                    self.get_vt_info(sample_hash)

    def get_malicious_sample_info(self, hash):
        info_url = self.api_url + "files/" + hash
        res = requests.post(info_url, headers=self.headers)
        if res.status_code == 200:
            result = res.json()
            if result.get("data").get("attributes").get("last-analysis-results"):
                stats = result.get("data").get("attributes").get("last-analysis-stats")
                malicious = str(stats.get("malicious"))
                undetected = str(stats.get("undetected"))
                print_info("Malicious", malicious)
                print_info("Undetected", undetected)
                results = result.get("data").get("attributes").get("last-analysis-results")
                self.display_malicious_findings(results)

class MalwareSample:
    
    def __init__(self, file) -> None:
        self.sample = file

    def get_basic_file_info(self):
        file_name = os.path.basename(self.sample)
        if "." in file_name:
            tmp = file_name.split(".")
            name = tmp[0]
            ext = tmp[1]
        else:
            name = file_name
            ext = None
        size = os.stat(self.sample).st_size
        kind = filetype.guess(self.sample)
        print_info("File name", name)
        print_info("Extension", ext)
        print_info("File size", size)
        if kind is None:
            kind = "Could not guess the file type"
        print_info("File type", kind)

    def generate_hashes(self):
        with open(self.sample, "rb") as f:
            self.binary = f.read()
        self.md5 = hashlib.md5(self.binary).hexdigest()
        self.sha1 = hashlib.sha1(self.binary).hexdigest()
        self.sha256 = hashlib.sha256(self.binary).hexdigest()
        self.sha512 = hashlib.sha512(self.binary).hexdigest()
        print_info("MD5", "\n "+self.md5)
        print_info("SHA1", "\n "+self.sha1)
        print_info("SHA256", "\n "+self.sha256)
        print_info("SHA512", "\n "+self.sha512)

    def extract_strings(self):
        strings = b2s.extract_all_strings(self.binary, min_chars=8, only_interesting=False)
        for string in strings:
            print(" " + string[0])

    def vt_check(self):
        try:
            api_url, api_key = load_config()
            if api_key == "" or api_key == "":
                print(f"{RED} [!] {RESET} Missing api_url or api_key")
                exit(1)
        except:
            print(f"{RED} [!] {RESET} Error loading API_URL and/or API_KEY")
            exit(1)
        vt = VTScan(self.sample, api_url, api_key)
        vt.analyze()

    def analyze(self):
        print_header("Basic File Info : ")
        self.get_basic_file_info()
        print()
        print_header("File Hashes : ")
        self.generate_hashes()
        print()
        print_header("Extracted Strings : ")
        self.extract_strings()
        print()
        print_header("VirusTotal Check : ")
        self.vt_check()

if __name__ == "__main__":
    init()
    GREEN = Fore.GREEN
    BLUE = Fore.BLUE
    YELLOW = Fore.YELLOW
    RED = Fore.RED
    GRAY = Fore.LIGHTBLACK_EX
    RESET = Fore.RESET

    args = sys.argv
    if len(args) != 2:
        print(f"{RED} [!] {RESET} Syntax : python3 statik.py <sample_file>")
        exit(1)
    
    file = sys.argv[1]
    if not os.path.exists(file):
        print(f"{RED} [!] {RESET} The file {file} does not exist")
        exit(1)
    if not os.path.isfile(file):
        print(f"{RED} [!] {RESET} The provided path does not point to a file")
        exit(1)

    sample = MalwareSample(file=file)
    sample.analyze()
