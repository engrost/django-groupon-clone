from django.db import models
from django.db.models.signals import post_save
from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes import generic
from photologue.models import ImageModel
from countries.models import Country
from tagging.fields import TagField
import datetime
import time

UPLOAD_TO = 'deal_images'

STATUS_ONHOLD = 1
STATUS_ACTIVE = 2
STATUS_REDEEMED = 3

STATUS = (
  (STATUS_ONHOLD, "Purchased - ON HOLD"),
  (STATUS_ACTIVE, "Purchased - Money Collected"),
  (STATUS_REDEEMED, "Redeemed"),
)


DAYS = (
    ( 1, 'Monday' ),
    ( 2, 'Tuesday' ),
    ( 3, 'Wednesday' ),
    ( 4, 'Thursday' ),
    ( 5, 'Friday' ),
    ( 6, 'Saturday' ),
    ( 7, 'Sunday' ),
)


PROVINCES = (
    ( 'ON' , 'Ontario' ),
    ( 'QC' , 'Quebec'  ),
    ( 'NS' , 'Nova Scotia' ),
    ( 'NB' , 'New Brunswick' ),
    ( 'MB' , 'Manitoba' ),
    ( 'BC' , 'British Columbia' ),
    ( 'PE' , 'Prince Edward Island' ),
    ( 'SK' , 'Saskatchewan' ),
    ( 'AB' , 'Alberta' ),
    ( 'NL' , 'Newfoundland and Labrador' ),
    ( 'YT' , 'Yukon Territory' ),
    ( 'NT' , 'Northwest Territories' ),
    ( 'NU' , 'Nunavut' ),
)
PROVINCES_d = dict(PROVINCES)

CC_TYPE_VISA = 1
CC_TYPE_MASTERCARD = 2
CC_TYPE_AMEX = 3

CC_TYPE = (
  (CC_TYPE_VISA, 'Visa'),
  (CC_TYPE_MASTERCARD, 'Mastercard'),
  (CC_TYPE_AMEX, 'American Express'),
)

class City(models.Model):
    """
    City database (latitude, longitude, postalcode)
    """
    name = models.CharField("City Name", max_length=60, unique=True)
    slug = models.SlugField(unique=True)
    # TODO: is_active is used for what?
    is_active = models.BooleanField(default=False)
    province = models.CharField("Province", max_length=2, choices=PROVINCES)
    order = models.IntegerField(default = 0)

    class Meta:
        verbose_name = 'City'
        verbose_name_plural = 'Cities'

    def __unicode__(self):
        return self.name

class Advertiser(models.Model):
    name       = models.CharField(max_length=60)
    address    = models.CharField(max_length=60)
    city       = models.ForeignKey(City)
    postalcode = models.CharField(max_length=7)
    province   = models.CharField(max_length=25, choices=PROVINCES)
    country    = models.ForeignKey(Country)
    phone      = models.CharField(max_length=25)
    phoneext   = models.CharField("Phone Ext", max_length=6, blank=True)
    cell       = models.CharField(max_length=25)
    fax        = models.CharField(max_length=25)
    contact    = models.CharField(max_length=50, blank=True, help_text="Advertising contact")
    email      = models.EmailField(blank=True, help_text="Email address of contact")
    
    def __unicode__(self):
        return self.name
    
    class Meta:
        verbose_name = 'Advertiser'

class ProductCategory(models.Model):
    """
    Categories for various products
    """
    
    name = models.CharField("Category", max_length=60)
    
    class Meta:
        verbose_name = 'Product Category'
        verbose_name_plural = 'Product Categories'
        
    def __unicode__(self):
        return self.name
    
class Deal(ImageModel):
    """
    Actual services
    """
    title                   = models.CharField("Title", max_length=256)
    advertiser            = models.ForeignKey('Advertiser', help_text="Deal's offer", verbose_name="Advertiser")
    city                    = models.ForeignKey(City)
    slug                    = models.SlugField()
    
    category                = models.ForeignKey(ProductCategory)
    date_published          = models.DateTimeField()
    retail_price            = models.DecimalField(default=0,decimal_places=2, max_digits=6, help_text='Full retail price')
    deal_price              = models.DecimalField(default=0,decimal_places=2, max_digits=6, help_text='Deal (real) Price')
    
    discount_percentage     = models.DecimalField(default=0,decimal_places=2, max_digits=6, help_text='% Percentage Off retail')
    discount_value          = models.DecimalField(default=0,decimal_places=2, max_digits=6, help_text='$ Dollars Off retail')
    auction_duration        = models.IntegerField(default=24, help_text='Deal duration in hours')
    
    is_deal_on              = models.BooleanField(default=False)
    fine_print              = models.TextField()
    highlights              = models.TextField()
    tipping_point           = models.IntegerField(default=1, help_text='What the hell is this')
    tipped_at               = models.DateTimeField()
    max_available           = models.IntegerField(default=0)
    description             = models.TextField()
    #  reviews                 = models.TextField()
    company_desc            = models.TextField()
    #  address                 = models.TextField()
    #  url                     = models.URLField()
    tags                    = TagField(help_text="Tags seperated by commas!!", verbose_name='tags')
    
    latitude                = models.DecimalField("Latitude (decimal)", max_digits=9, decimal_places=6, blank=True, null=True)
    longitude               = models.DecimalField("Longitude (decimal)", max_digits=9, decimal_places=6, blank=True, null=True)
    
    entry_date              = models.DateTimeField(blank=True, editable=False, null=True, auto_now_add=True)
    last_mod                = models.DateTimeField(blank=True, editable=False, null=True, auto_now=True)
    deleted_date            = models.DateTimeField(blank=True, editable=False, null=True)
    
    class Meta:
        verbose_name = 'Deal'
        verbose_name_plural = 'Deals'
        
    def __unicode__(self):
        return self.title
    
    @models.permalink
    def get_absolute_url(self):
        return ('deal-detail', [self.slug])
    
    def num_available(self):
        return self.max_available - self.num_sold()
    
    def num_sold(self):
        return self.coupon_set.count()

    def percentage_sold(self):
        num_sold = self.num_sold()
        if num_sold > self.tipping_point:
            return 100
        else:
            return int( ( (num_sold*1.0) / self.tipping_point) * 100)
        
    def num_needed(self):
        num_sold = self.num_sold()
        if num_sold > self.tipping_point:
            return 0
        else:
            return self.tipping_point - num_sold

    def time_left(self):
        now = datetime.datetime.now()
        expired_at = self.date_published + datetime.timedelta(hours=self.auction_duration)
        
        if expired_at < now :
            return "Request closed"
        
        expire_time =  expired_at - now
        expire_time_hours = int(time.strftime("%H", time.gmtime(expire_time.seconds)))
        expire_time_mins = int(time.strftime("%M", time.gmtime(expire_time.seconds)))
        
        if expire_time.days < 1:
            if expire_time_hours < 1:
                if expire_time_mins < 1:
                    if expire_time.seconds < 1:
                        return "Request closed"
                    else:
                        return "%d seconds" % expire_time.seconds
                else:
                    return "%d minutes" % expire_time_mins
            else:
                return "%d hours, %d minutes" % (expire_time_hours, expire_time_mins)
        else:
            if expire_time_hours < 1:
                return "%d days" % (expire_time.days)
            else:
                return "%d days, %d hours" % (expire_time.days, expire_time_hours)
    
    def is_expired(self):
        now = datetime.datetime.now()
        expired_at = self.date_published + datetime.timedelta(hours=self.auction_duration)
        
        return expired_at < now

 
class EmailSubscribe(models.Model):
    email      = models.EmailField(help_text="Email address of contact")
    city       = models.ForeignKey(City)
    
    class Meta:
        verbose_name = 'Email subscribe'
        verbose_name_plural = 'Email subscribes'
        unique_together = ( ('city', 'email'),)
        
    def __unicode__(self):
        return self.email


class Profile(models.Model):
    """
    User profile 
    """
    user            = models.OneToOneField(User)
    is_email_sub    = models.BooleanField(default=False)
    streetnumber    = models.CharField("Street Number", max_length=10, blank=True, null=True)
    street          = models.CharField("Street Name", max_length=40, blank=True, null=True)
    apt             = models.CharField("Apartment #", max_length=20, blank=True, null=True)
    city            = models.ForeignKey(City, blank=True, null=True)
    postalcode      = models.CharField("Postal Code", max_length=7, blank=True, null=True)
    province        = models.CharField(max_length=25, choices=PROVINCES, blank=True, null=True)
    country         = models.ForeignKey(Country, blank=True, null=True)
    
    phone           = models.CharField(blank=True, max_length=16)
    phoneext        = models.CharField("Phone Ext", max_length=6, blank=True)
    cell            = models.CharField("Cell #", blank=True, max_length=16)
    fax             = models.CharField(blank=True, max_length=16)
    
    class Meta:
        verbose_name = 'Profile'
        verbose_name_plural = 'Profiles'
        
    def __unicode__(self):
        return self.phone
    
    def is_filled(self):
        return self.user.email and self.user.first_name and self.user.last_name
    
    def fill_from_facebook(self, info):
        # TODO: Check if email is unique (we might end up with same user from facebook and twitter)
        self.user.email = info.get('email', '')
        self.user.first_name = info.get('first_name', '')
        self.user.last_name = info.get('last_name', '')
        self.user.save()

# Automatically create user profiles when a user is created
def create_user_profile(sender, instance, created, **kwargs):
    if created:
        Profile.objects.create(user=instance)

post_save.connect(create_user_profile, sender=User)


class Coupon(models.Model):
    user                    = models.ForeignKey(User)
    deal                    = models.ForeignKey(Deal)
    status                  = models.IntegerField(choices=STATUS, default=0)
    entry_date              = models.DateTimeField(blank=True, editable=False, null=True, auto_now_add=True)
    last_mod                = models.DateTimeField(blank=True, editable=False, null=True, auto_now=True)
    deleted_date            = models.DateTimeField(blank=True, editable=False, null=True)
    
    class Meta:
        verbose_name = 'Coupon'
        verbose_name_plural = 'Coupons'
    
    def __unicode__(self):
        return str(self.user)
