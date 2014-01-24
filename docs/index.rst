Claimed Email Login Authentication
==================================

Contents:

.. toctree::
   :maxdepth: 2

   design
   ux
   formalization


Summary
-------

The ``celauth`` Python library implements the "Claimed Email Login" (CEL)
authentication model with OpenID_ and Django_. The Python library is designed to
be work "out of the box" (with two working examples) and allow customization of
user interaction details such as look and feel.

Motivation
----------

The primary motivation for ``celauth`` is the same as OpenID_, in particular,
not requiring users to manage yet another password for every new website they
sign up for. Additional motivations are to address some of the potential
downsides of using OpenID_, namely single OpenID provider points of failure and
user confusion due to forgetting which login option has been used to log into
an account.

http://www.stackexchange.com/ has provided insipiration for much of the design.

Examples
--------

The ``celauth`` Python library comes with two examples, both using Django but
only one of them using ``django.contrib.auth``.

miniauth example
~~~~~~~~~~~~~~~~

The miniauth example is the smaller example, only using incremented numbers as account
identification and not using the user model from ``django.contrib.auth``.


djadmin example
~~~~~~~~~~~~~~~

The djadmin example uses the ``django.contrib.auth`` and ``django.contrib.admin`` applications
but replaces the traditional username/password authentication and registration with the Claimed
Email Login system of ``celauth``. This example works "out of the box" with the Django admin app.


Other Libraries
===============

Other OpenID related Python libraries worth mentioning:

* https://github.com/openid/python-openid (used by ``celauth``)
* https://github.com/pennersr/django-allauth
* https://launchpad.net/django-openid-auth
* https://github.com/omab/python-social-auth
* http://code.google.com/p/django-openid-consumer/


Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`

.. _OpenID: http://openid.net/
.. _Django: http://www.djangoproject.com

