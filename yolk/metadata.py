#!/usr/bin/python
# -*- coding: utf-8 -*-
# pylint: disable-msg=C0301,W0613,W0612

"""

metadata.py
===========

Author   : Rob Cakebread <gentoodev@gmail.com>

License  : PSF (Python Software Foundation License)

Desc     : Return metadata for Python distribution installed by setuptools
           in a dict

           Note: The metadata uses RFC 2822-based message documents.

"""

__docformat__ = 'restructuredtext'

import email


def get_metadata(dist):
    """Return dictionary of metadata for given dist"""
    if not dist.has_metadata('PKG-INFO'):
        return

    md = dist.get_metadata('PKG-INFO')
    msg = email.message_from_string(md) 
    metadata = {}
    for header in [l for l in msg._headers]:
        metadata[header[0]] = header[1]

    return metadata

