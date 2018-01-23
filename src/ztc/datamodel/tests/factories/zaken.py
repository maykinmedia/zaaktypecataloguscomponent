import factory

from ztc.datamodel.models import (
    BronCatalogus, BronZaakType, Formulier, ProductDienst, ReferentieProces,
    ZaakObjectType, ZaakType
)

from .catalogus import CatalogusFactory
from .relatieklassen import ZaakTypenRelatieFactory

ZAAKTYPEN = [
    'Melding behandelen',
    'Toetsing uitvoeren',
    'Vergunningaanvraag regulier behandelen',
    'Vergunningaanvraag uitgebreid behandelen',
    'Vooroverleg voeren',
    'Zienswijze behandelen',
    'Bestuursdwang ten uitvoer leggen',
    'Handhavingsbesluit nemen',
    'Handhavingsverzoek behandelen',
    'Last onder dwangsom ten uitvoer leggen',
    'Toezicht uitvoeren',
    'Advies verstrekken',
    'Beroep behandelen',
    'Bezwaar behandelen',
    'Incidentmelding behandelen',
    'Voorlopige voorziening behandelen',
]


class ProductDienstFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ProductDienst


class FormulierFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = Formulier


class ReferentieProcesFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = ReferentieProces


class BronCatalogusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = BronCatalogus


class BronZaakTypeFactory(factory.django.DjangoModelFactory):
    zaaktype_identificatie = factory.sequence(lambda n: n)

    class Meta:
        model = BronZaakType


class ZaakTypeFactory(factory.django.DjangoModelFactory):
    zaaktype_identificatie = factory.Sequence(lambda n: n)
    doorlooptijd_behandeling = 30
    verlengingstermijn = 30
    trefwoord = []  # ArrayField has blank=True but not null=True
    verantwoordingsrelatie = []  # ArrayField has blank=True but not null=True
    maakt_deel_uit_van = factory.SubFactory(CatalogusFactory)
    referentieproces = factory.SubFactory(ReferentieProcesFactory)

    # this one is optional, if its added as below, it will keep adding related ZaakTypes (and reach max recursion depth)
    # heeft_gerelateerd = factory.RelatedFactory(ZaakTypenRelatieFactory, 'zaaktype_van')

    class Meta:
        model = ZaakType

    @factory.post_generation
    def is_deelzaaktype_van(self, create, extracted, **kwargs):
        # optional M2M, do nothing when no arguments are passed
        if not create:
            return

        if extracted:
            for zaaktype in extracted:
                self.is_deelzaaktype_van.add(zaaktype)

    @factory.post_generation
    def product_dienst(self, create, extracted, **kwargs):
        # required M2M
        if not extracted:
            extracted = [ProductDienstFactory.create()]

        for product_dienst in extracted:
            self.product_dienst.add(product_dienst)


class ZaakObjectTypeFactory(factory.django.DjangoModelFactory):
    is_relevant_voor = factory.SubFactory(ZaakTypeFactory)

    class Meta:
        model = ZaakObjectType
