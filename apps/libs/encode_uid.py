""" memperpendek uid

dari uid A1:B1:C1:D1 jadi A1B1C1D1
"""


def encode_uid(uid: str) -> str:
    uid = uid.replace(':', '')
    return uid
