from django.db import models

class Account(models.Model):
    # django.models.Model will create id attribute
    def __unicode__(self):
        return u"Account %i" % (self.id)

