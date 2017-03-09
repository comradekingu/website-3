from django.db import models
from django.contrib.auth.models import User
from django.utils.encoding import python_2_unicode_compatible

import markdown

import datetime


@python_2_unicode_compatible
class Category(models.Model):
    """
    A category that an entry can belong to.

    """
    title = models.CharField(
        max_length = 250
        )
    slug = models.SlugField(
        unique = True,
        help_text = u'Used in the URL for the category. Must be unique.'
        )
    description = models.TextField(
        help_text = u'A short description of the category, to be used in list pages.'
        )
    description_html = models.TextField(
        editable = False,
        blank = True
        )

    class Meta(object):
        verbose_name_plural = 'Categories'
        ordering = ['title']

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        self.description_html = markdown.markdown(self.description)
        super(Category, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
         return ('news-category', (), { 'slug': self.slug })


@python_2_unicode_compatible
class Entry(models.Model):
    # Metadata.
    author = models.ForeignKey(User)
    pub_date = models.DateTimeField(
        u'Date posted',
        default=datetime.datetime.today,
        )
    slug = models.SlugField(
        unique_for_date = 'pub_date',
        help_text = u'Used in the URL of the entry. Must be unique for the publication date of the entry.'
        )
    title = models.CharField(max_length=250)

    # The actual entry bits.
    body = models.TextField()
    body_html = models.TextField(editable = False, blank = True)
    excerpt = models.TextField(blank = True, null = True)
    excerpt_html = models.TextField(blank = True, null = True, editable = False)

    # Categorization.
    categories = models.ManyToManyField(
        Category,
        blank = False
        )

    class Meta(object):
        get_latest_by = 'pub_date'
        ordering = ['-pub_date']
        verbose_name_plural = 'Entries'

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if self.pub_date is None:
            self.pub_date = datetime.datetime.now()
        if self.excerpt:
            self.excerpt_html = markdown.markdown(self.excerpt)
        self.body_html = markdown.markdown(self.body, safe_mode = True)
        super(Entry, self).save(*args, **kwargs)

    @models.permalink
    def get_absolute_url(self):
         return ('news-entry', (), {
                'year': self.pub_date.strftime('%Y'),
                'month': self.pub_date.strftime('%m'),
                'day': self.pub_date.strftime('%d'),
                'slug': self.slug })


