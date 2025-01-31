from django.db import models
from django.test import TestCase, override_settings
from django.utils.text import slugify
from edc_utils import get_utcnow

from edc_search.model_mixins import SearchSlugModelMixin
from edc_search.search_slug import SearchSlug
from edc_search.updater import SearchSlugDuplicateFields

from ..models import TestModel, TestModelDuplicate, TestModelExtra


@override_settings(
    EDC_AUTH_SKIP_SITE_AUTHS=False,
    EDC_AUTH_SKIP_AUTH_UPDATER=False,
)
class TestSearchSlug(TestCase):
    def test_search_slug_no_fields(self):
        search_slug = SearchSlug()
        self.assertEqual(search_slug.slug, "")

    def test_search_slug_with_fields(self):
        class MyModel(SearchSlugModelMixin, models.Model):
            f1 = models.IntegerField(default=1)
            f2 = models.IntegerField(default=2)

        search_slug = SearchSlug(obj=MyModel(), fields=["f1", "f2"])
        self.assertEqual(search_slug.slug, "1|2")

    def test_gets_slug(self):
        dt = get_utcnow()
        obj = TestModel(f1="erik is", f2=dt, f3=1234)
        obj.save()
        self.assertEqual(obj.slug, f"erik-is|{slugify(dt)}|1234|attr|dummy|dummy_attr")

    def test_gets_with_none(self):
        obj = TestModel(f1=None, f2=None, f3=None)
        obj.save()
        self.assertEqual(obj.slug, "|||attr|dummy|dummy_attr")

    def test_gets_with_inherit(self):
        obj = TestModelExtra(
            f1="i am from testmodel", f2=None, f3=None, f4="i am from testmodelextra"
        )
        obj.save()
        self.assertEqual(
            obj.slug,
            "i-am-from-testmodel|||attr|dummy|dummy_attr|i-am-from-testmodelextra",
        )

    def test_duplicates(self):
        obj = TestModelDuplicate(
            f1="i am from testmodel", f2=None, f3=None, f4="i am from testmodelextra"
        )
        self.assertRaises(SearchSlugDuplicateFields, obj.save)

    def test_too_long(self):
        obj = TestModel.objects.create(f1="x" * 300)
        obj.save()
        self.assertIsNotNone(obj.search_slug_warning)
        self.assertEqual(len(obj.slug), 250)
        obj = TestModel.objects.all()[0]
        obj.save()

    def test_updater(self):
        obj = TestModel.objects.create(f1="x" * 300)
        obj.save()
        obj.slug = None
        obj.save_base()
        obj = TestModel.objects.all()[0]
        self.assertIsNone(obj.slug)
        TestModel.objects.update_search_slugs()
        obj = TestModel.objects.all()[0]
        self.assertIsNotNone(obj.slug)
