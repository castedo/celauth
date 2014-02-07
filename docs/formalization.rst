Formalization
=============

The claimed email login model is based on a mathematical formalization. The main class used in unit testing is implemented closely to this formalization.

Unit Testing Code
-----------------

.. automodule:: celauth.tests

.. autoclass:: celauth.tests.TestCelRegistryStore
   :members: __init__


Math Formalization
------------------

Most of the state is captured by the "registry", represented below as :math:`R`. This is the global state of the system across all accounts, email addresses and login IDs.

.. math::

   R = (f, g, h, A, B, C)

where

=========  ==============================================
=========  ==============================================
:math:`f`  Maps login IDs to accounts.
:math:`g`  Maps email addresses to accounts.
:math:`h`  Maps confirmation codes to email addresses.
:math:`A`  Set of all claims.
:math:`B`  Subset of all credible claims.
:math:`C`  Subset of all confirmed claims.
=========  ==============================================


The state of the CEL registry can be represented visually as shown below.

Example Registry Diagram
++++++++++++++++++++++++

.. graphviz:: _build/many_accounts.dot


Key:

=================  =================
=================  =================
accounts           blue background
confirmed claims   thick green lines
credible claims    solid lines
incredible claims  red dashed lines
=================  =================


Account Creation without confirmation
+++++++++++++++++++++++++++++++++++++

.. graphviz:: _build/not_confirmed.dot

Confirmation before Account Creation
++++++++++++++++++++++++++++++++++++

.. graphviz:: _build/confirmed_before.dot

