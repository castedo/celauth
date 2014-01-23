Claimed Email Login Design
==========================

Design Goals
------------

The ``celauth`` Python library and the Claimed Email Login model have been
designed with the usability and security objectives in mind together with a
mathematically precise state model to cover all corner cases. Usability and
security/privacy goals often have conflicting solutions. CEL model tries to
strike a balance with some options to favor one objective over the other.

User-oriented Goals:

* minimize confusion by using email addresses as the most intuitive form of identification
* make possible user registration with zero typing or pasting
* allow single accounts to have multiple ``login ID`` (OpenID, OAuth or traditional username/password, etc...)
* allow single accounts to have multiple email addresses

Security/Privacy Goals:

* do not let compromised email accounts escalate to access to existing user accounts
* make it possible to prevent untrusted OpenID logins from discovering what
email addresses are registered with accounts

Developer-oriented Goals:

* make it easy for web developers to add the "Claimed Email Login" to their website
* a mathematically defined foundation to check all corner cases against


Concepts
--------

Account
  The settings, data, resources etc..., attributed in some restricted way to a web site user.

Address
  When written without qualification, an ``address`` is an email address, not web address.

Login ID
  Normally an OpenID but other login mechanisms such as traditional
  username/password and OAuth could also serve an equivalent roll of OpenID as
  authentication option.
  
User
  The CEL model definition and ``celauth`` Python library avoid using or defining the term ``user``
  since different application may present or conceptualize a ``user`` in different ways. For instance,
  the Django framework has the concept of an anonymous user which in the above CEL concepts is neither
  a login ID nor an account.

Claim
  Claims on email addresses are made by Login IDs. By themselves, claims have
  no side-effect other than possibly causing email to be sent to the email
  address. Claims may additionally be flagged as confirmed or just credible.

Confirmed Claim
  A claim where a Login IDs has confirmed it could read a random confirmation
  code sent to the claimed email address.

Credible Claim
  Some OpenID identify providers are flagged by the administrator as providing
  'credible' email addresses. This conveys a _minor_ amount of privilege, namely being able to discover
  whether an account exists for the claimed email address. It does not provide the full privileges of a
  confirmed claim. Claim credibility is largely invisible to the user and is mainly a trade-off for website
  administrators to make registration faster.

Basics
------

* Every account has one or more Login IDs (OpenIDs, username/password, OAuth, etc...)
* A Login ID only provides access to at most one account
* An email address is granted to at most one user account


Privileges
----------

There are three levels of privilege, with each level having all the privileges of the lesser levels.

1. Login ID

  * claim an email address (usually resulting in email sent to the claimed address)

2. Login ID with credible email addresses

  * Ability to view list of login ID that have claimed a specific email address
    and whether an account exists with claims to that email address.
  * can create new account with claimed addresses not claimed by any other accounts.

3. Account

  * Permissions granted to an email address are granted to the account with that (confirmed) email address.


Privilege Escalation
++++++++++++++++++++

A visitor has a credible email address by one of two means:

* providing a confirmation code sent to that email address
* logging in with an (OpenID) identity provider that provides credible email address

It up to site administrator to choose which (OpenID) identify providers provide
credible email addresses or not. There is a trade-off in usability vs privacy/security in this choice.

A Login ID with credible email address can create an account. That account will have the permissions of any email addresses granted to that account (when that email is confirmed and not granted to another account).

