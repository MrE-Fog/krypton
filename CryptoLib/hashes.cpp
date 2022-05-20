#include "CryptoLib.h"

#include <openssl/evp.h>
#include <openssl/rand.h>
#include <pybind11/pybind11.h>

using namespace std;
namespace py = pybind11;

const int AES_KEY_LEN = 32;
const int IV_SALT_LEN = 12;
const auto PBKDF2_HASH_ALGO = EVP_sha512;

char* __cdecl PBKDF2(char* text, char* salt, int iter) {
	char* key = new char[AES_KEY_LEN];
	int len = strlen(text);
	int a;
	a = PKCS5_PBKDF2_HMAC(text, len, (const unsigned char*) salt, IV_SALT_LEN, iter, PBKDF2_HASH_ALGO(), AES_KEY_LEN, (unsigned char*)key);
	OPENSSL_cleanse(text, len);
	if (a != 1) {
		throw std::invalid_argument("Unable to hash data.");
	}
	return key;
};

py::bytes __cdecl pySHA512(py::bytes text) {
	char result[64];
	int len = 64;
	EVP_Q_digest(NULL, "sha512", NULL, text.cast<char*>(), 
		text.attr("__len__")().cast<int>(), (unsigned char*)&result, 
		(size_t *)&len);
	py::bytes result = py::bytes(result, 64);
}
