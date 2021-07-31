﻿// Cross-PlatformCryptoLib.cpp : Defines the entry point for the application.

#include "Cross-PlatformCryptoLib.h"
#ifndef Win
#define DLLEXPORT
#endif
#ifdef Win
#define DLLEXPORT __declspec(dllexport)
#endif
#define PY_SSIZE_T_CLEAN

#include <openssl/crypto.h>
#include <openssl/rand.h>
#include <string.h>
#include <cmath>
#include <string>
#include <openssl/conf.h>
#include <openssl/evp.h>
#include <openssl/err.h>

extern "C" {

	void handleErrors(int* err) {
		//Add to log here
		*err = *err + 1;
	}
		DLLEXPORT int __cdecl AddToStrBuilder(char* buffer,char* content, int len) {
			memcpy_s(buffer+len, strlen(content), content, strlen(content));
			return 0;
		}

		DLLEXPORT unsigned char* __cdecl AESEncrypt(unsigned char* texta, unsigned char* key, char* ivbuff, char* tag) {
			int errcnt = 0;
			int msglen = strlen((char*)texta);
			
			int rem = 16 - remainder(msglen, 16);
			unsigned char* text = new unsigned char[msglen+(long long)rem];
			memcpy_s(text, msglen, texta, msglen);
			memset(text + msglen, 0, rem);
			OPENSSL_cleanse(texta, strlen((char*)texta));
			
			unsigned char iv[12];
			RAND_bytes(iv, 12);
			memcpy_s(ivbuff, 12, iv, 12);
			unsigned char* out = new unsigned char[msglen+(long long)rem];
			/*
			AES_KEY aes_key;
			AES_set_encrypt_key(key, 256, &aes_key);
			AES_cbc_encrypt(text, out, msglen + (long long)rem, &aes_key, iv, AES_ENCRYPT);

			OPENSSL_cleanse((void*)text, sizeof((const char*)text));
			OPENSSL_cleanse((void*)key, sizeof((const char*)key));
			OPENSSL_cleanse(&aes_key, sizeof(aes_key));
			delete[] text;

			return out;
			*/
			EVP_CIPHER_CTX* ctx;
			int len;
			int ciphertext_len;
			if (!(ctx = EVP_CIPHER_CTX_new()))
				handleErrors(&errcnt);
			if (1 != EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL))
				handleErrors(&errcnt);

			if (1 != EVP_EncryptInit_ex(ctx, NULL, NULL, key, iv))
				handleErrors(&errcnt);

			if (1 != EVP_EncryptUpdate(ctx, out, &len, text, msglen))
				handleErrors(&errcnt);
			ciphertext_len = len;

			if (1 != EVP_EncryptFinal_ex(ctx, out + len, &len))
				handleErrors(&errcnt);

			if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, 16, tag))
				handleErrors(&errcnt);
			ciphertext_len += len;
			EVP_CIPHER_CTX_free(ctx);

			OPENSSL_cleanse((void*)text, sizeof((const char*)text));
			OPENSSL_cleanse((void*)key, sizeof((const char*)key));
			if (errcnt != 0) {
				unsigned char error[] = "Error";
				return error;
			}
			return out;
		}

		DLLEXPORT unsigned char* __cdecl AESDecrypt(unsigned char* iv, unsigned char* key, unsigned char* ctext, char* tag) {
			int errcnt = 0;
			int msglen = strlen((char*)ctext);
			/*
			unsigned char* ctext = new unsigned char[msglen];
			memcpy(ctext, ctexta, msglen);
			*/
			unsigned char* out = new unsigned char[msglen];
			/*
			AES_KEY aes_key;
			AES_cbc_encrypt(ctext, out, msglen + (long long)rem, &aes_key, iv, AES_DECRYPT);
			*/
			EVP_CIPHER_CTX* ctx;
			int len;
			int plaintext_len;
			if (!(ctx = EVP_CIPHER_CTX_new()))
				handleErrors(&errcnt);
			if (!EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL))
				handleErrors(&errcnt);
			if (!EVP_DecryptInit_ex(ctx, NULL, NULL, key, iv))
				handleErrors(&errcnt);
			if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, 16, tag))
				handleErrors(&errcnt);
			if (1 != EVP_DecryptUpdate(ctx, out, &len, ctext, msglen))
				handleErrors(&errcnt);
			plaintext_len = len;
			if (1 != EVP_DecryptFinal_ex(ctx, out + len, &len))
				handleErrors(&errcnt);
			plaintext_len += len;
			int ret = EVP_DecryptFinal_ex(ctx, out + len, &len);
			
			EVP_CIPHER_CTX_free(ctx);
			OPENSSL_cleanse((void*)ctext, sizeof((const char*)ctext));
			OPENSSL_cleanse((void*)key, sizeof((const char*)key));
			OPENSSL_cleanse(&iv, sizeof(iv));

			if (ret>0) {
				unsigned char error[] = "Error";
				return error;
			}
			if (errcnt > 0) {
				unsigned char error[] = "Error";
				return error;
			}
			return out;
		}
	
}
/*
namespace Cpp {
	std::initializer_list<std::string> AESEncrypt(char* textb, char* keyb) {
		char* iv = new char[8];
		char* a = (char*)C::AESEncrypt((unsigned char*)textb, (unsigned char*)keyb, iv);
		OPENSSL_cleanse(textb, sizeof(textb));
		OPENSSL_cleanse(keyb, sizeof(keyb));
		auto result = { std::string(iv), std::string(a) };
		delete[] a;
		delete[] iv;
		return result;
	}


	std::string AESDecrypt(char* iv, char* key, char* ctext) {
		char* a = (char*)C::AESDecrypt((unsigned char*)iv, (unsigned char*)key, (unsigned char*)ctext);  //We believe it is unecesary to delete arguments passed inside functions as it is passed as reference
		OPENSSL_cleanse(key, strlen(key));
		std::string result = std::string(a);
		OPENSSL_cleanse(a, strlen(a));
		delete[] a;
		return result;
	}
}
*/
DLLEXPORT int __cdecl Init() {
	EVP_add_cipher(EVP_aes_256_gcm());
	if (FIPS_mode_set(2) == 0) {
		return 0;
	}
	return 1;
}
