from django.db import models

from users.models import User



class CommonModel(models.Model):

    """
    A common abstract class for inheriting some common fields
    """

    created_date = models.DateField(auto_now_add=True, blank=True, null=True)
    updated_datetime = models.DateTimeField(auto_now=True, blank=True, null=True)
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, related_name='+', 
                                        blank=True, null=True, on_delete=models.SET_NULL)
    updated_by = models.ForeignKey(User, related_name='+',
                                        blank=True, null=True, on_delete=models.SET_NULL)

    class Meta:
        abstract = True


DOC_TYPE_CHOICES = (
    ('STF', 'Staff'),
    ('PRD', 'Product'),
    ('CRY', "Category"),
    ("CUS", "Customer"),
    ("OFR", "Offer"),
    ("ORD", "Order"),
)

class DocumentNumber(models.Model):

    """
    Table for generating numbers for models
    """
    doc_type = models.CharField(max_length=50, choices=DOC_TYPE_CHOICES)
    number = models.CharField(max_length=100)

    def save(self, *args, **kwargs):
        preivious_doc = DocumentNumber.objects.filter(doc_type=self.doc_type).order_by('id').last()
        if not preivious_doc:
            number = '000001'
        else:
            number = preivious_doc.number
            number = int(number)
            number += 1
            number = str(number)
            number = number.zfill(6)
        self.number = number
        super().save(*args, **kwargs)

    def __str__(self):
        return f'{self.doc_type}{self.number}'