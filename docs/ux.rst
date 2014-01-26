Authentication User Interaction
===============================

Below is a diagram of the authentication interaction for new users. This
interaction is from the perspective of authentication and authentication
relevant events, not user experience details like what user interface elements
are show together or at what stages. 

.. graphviz::

   digraph {
      rankdir=TB;
      login [label="Log In"];
      {
        rank=same;
        enter_email [label="Enter\nAddress"];
        confirm_email [label="Confirm\nEmail"];
        create_account [label="Create\nAccount"];
        join_account [label="Join\nAccount"];
      }
      account_access [label="Account\nAccessed"];
      login -> enter_email [label="M", labeldistance=-80];
      login -> confirm_email;
      login -> create_account;
      login -> join_account;
      login -> account_access;
      // there seems to be a graphviz bug requiring dir=back
      enter_email -> confirm_email;
      confirm_email -> create_account;
      confirm_email -> account_access [label="A"];
      create_account -> account_access;
      join_account -> account_access;
   }

Key:

=== =================
=== =================
 M   OpenID login is missing email address
 A   Account already assigned to email address
=== =================


Authentication interaction when visitor enters email address first instead of
choosing a login mechanisms (e.g. an OpenID provider):

.. graphviz::

   digraph {
      rankdir=LR;
      enter_email_anon [label="Enter\nAddress"];
      confirm_email_anon [label="Confirm\nEmail"];
      logins_found [label="Show\nClaiming\nLogins"];
      enter_email_anon -> confirm_email_anon
      confirm_email_anon -> logins_found
   }
