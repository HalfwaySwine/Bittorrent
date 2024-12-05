from urllib.parse import urlparse, quote_plus, unquote, quote, unquote_plus
import bencoder
import hashlib

expected_info_hash_url_encoded = "%F3%1BC%C3%A4%1E%D3%F3%F3%A4%D7%83%1E~%9D%5E%94ED9"
unquoted = unquote_plus(expected_info_hash_url_encoded)
beginning = quote_plus(unquoted)
# http://bttracker.debian.org:6969/announce?info_hash=%F3%1BC%C3%A4%1E%D3%F3%F3%A4%D7%83%1E~%9D%5E%94ED9&peer_id=-TR4060-ycy5wnwi2uvz&port=51413&uploaded=0&downloaded=0&left=659554304&numwant=80&key=3F984309&compact=1&supportcrypto=1&event=started


def test_url_encoding():
    hash = "\x12\x34\x56\x78\x9a\xbc\xde\xf1\x23\x45\x67\x89\xab\xcd\xef\x12\x34\x56\x78\x9a"
    hash = "123456789abcdef123456789abcdef123456789a"
    infohash_array = bytes.fromhex(hash)
    urlencoded_info_hash = quote_plus(infohash_array.decode("utf-8", errors="replace"))
    print(urlencoded_info_hash)
    expect = "%124Vx%9A%BC%DE%F1%23Eg%89%AB%CD%EF%124Vx%9A"


def test_info_dict_hashing():
    torrent_file = "tests/fixtures/debian-mac.torrent"
    with open(torrent_file, "rb") as f:
        torrent_data = bencoder.bdecode(f.read())
    info_dict = torrent_data[b"info"]
    info_dict_bencoded = bencoder.bencode(info_dict)
    hash_obj = hashlib.sha1(info_dict_bencoded)
    hash = hash_obj.digest()
    urlencoded_info_hash = quote_plus(hash.decode("utf-8", errors="replace"))
    print(urlencoded_info_hash)
    # Result: "%EF%BF%BD%1BC%C3%A4%1E%EF%BF%BD%EF%BF%BD%EF%BF%BD%D7%83%1E~%EF%BF%BD%5E%EF%BF%BDED9"
