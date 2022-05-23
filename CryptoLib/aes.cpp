#include "CryptoLib.h"

#include <pybind11/pybind11.h>
#include <openssl/crypto.h>
#include <openssl/rand.h>
#include <openssl/evp.h>
#include <iostream>

using namespace std;
namespace py = pybind11;

int MAX_CRYPTO_LEN = 549755813632;
const int AES_KEY_LEN = 32;
const int IV_SALT_LEN = 12;
const int AUTH_TAG_LEN = 16;
py::bytes __cdecl AESEncrypt(char* textc, py::bytes key, int msglenc) {
	if (key.attr("__len__")().cast<int>() != 32){
		throw std::invalid_argument("Key is of wrong size");
	}
	py::bytes ftext =  py::bytes("$") + py::bytes((char*)&msglenc, 1) + py::bytes(textc, msglenc);
	int msglen = ftext.attr("__len__")().cast<int>();
	char* text = pymbToBuffer(ftext);
	char* k = pymbToBuffer(key);
	py::gil_scoped_release release;
	int rem = AUTH_TAG_LEN - (msglen % AUTH_TAG_LEN);
	int flen = msglen + (long long)rem + (long long)AUTH_TAG_LEN + (long long)IV_SALT_LEN;
	auto out = unique_ptr<unsigned char[]>(new unsigned char[flen]);
	unsigned char* iv = out.get() + flen - (long long)IV_SALT_LEN;
	RAND_bytes(iv, IV_SALT_LEN);
	unsigned char* tag = out.get() + flen - (long long)IV_SALT_LEN - (long long)AUTH_TAG_LEN;

	EVP_CIPHER_CTX* ctx;
	int len;
	int ciphertext_len;
	if (!(ctx = EVP_CIPHER_CTX_new()))
		handleErrors();
	if (1 != EVP_EncryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL))
		handleErrors();
	if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, IV_SALT_LEN, NULL))
		handleErrors();
	if (1 != EVP_EncryptInit_ex(ctx, NULL, NULL, (unsigned char*)k, iv))
		handleErrors();
	if (1 != EVP_EncryptUpdate(ctx, out.get(), &len, (unsigned char*)text, msglen))
		handleErrors();
	ciphertext_len = len;
	if (1 != EVP_EncryptFinal_ex(ctx, out.get() + len, &len))
		handleErrors();
	if (1 != EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_GET_TAG, AUTH_TAG_LEN, &tag))
		handleErrors();
	ciphertext_len += len;
	OPENSSL_cleanse(text, msglen);
	OPENSSL_cleanse(k, 32);
	delete[] k;
	EVP_CIPHER_CTX_free(ctx);
	py::gil_scoped_acquire acquire;
	py::bytes bresult = py::bytes((const char*)out.get(), flen);
	return bresult;
}

py::bytes __cdecl AESDecrypt(py::bytes ctext_b, py::bytes key){
	if (key.attr("__len__")().cast<int>() != 32){
		throw std::invalid_argument("Key is of wrong size");
	}
	int input_len = ctext_b.attr("__len__")().cast<int>();
	char* b = pymbToBuffer(ctext_b);
	char* k = pymbToBuffer(key);
	py::gil_scoped_release release;

	int msglen = input_len - AUTH_TAG_LEN - IV_SALT_LEN;
	auto out = unique_ptr<unsigned char[]>(new unsigned char[msglen + (long long)1]);
	unsigned char* iv = (unsigned char*)b + input_len - IV_SALT_LEN;
	unsigned char* tag = (unsigned char*)b + msglen;
	EVP_CIPHER_CTX* ctx;
	int len;
	int plaintext_len;
	if (!(ctx = EVP_CIPHER_CTX_new()))
		handleErrors();
	if (!EVP_DecryptInit_ex(ctx, EVP_aes_256_gcm(), NULL, NULL, NULL))
		handleErrors();
	if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_IVLEN, IV_SALT_LEN, NULL))
		handleErrors();
	if (!EVP_DecryptInit_ex(ctx, NULL, NULL, (unsigned char*)k, iv))
		handleErrors();
	if (1 != EVP_DecryptUpdate(ctx, out.get(), &len, (const unsigned char*)b, msglen))
		handleErrors();
	plaintext_len = len;
	if (!EVP_CIPHER_CTX_ctrl(ctx, EVP_CTRL_GCM_SET_TAG, AUTH_TAG_LEN, tag))
		handleErrors();
	int ret = EVP_DecryptFinal_ex(ctx, out.get() + len, &len);
	plaintext_len += len;
	EVP_CIPHER_CTX_free(ctx);
	OPENSSL_cleanse(k, 32);
	if (!(ret >= 0)) {
		throw std::invalid_argument("Unable to decrypt ciphertext");
	}
	out[plaintext_len] = '\0';
	int plainMsgLen = out.get()[1];
	py::gil_scoped_acquire acquire;
	return py::bytes((char*)out.get() + 2, plainMsgLen);
}
