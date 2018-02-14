from django.test import TestCase
from django.urls import reverse

from freezegun import freeze_time

from ztc.datamodel.tests.base_tests import HaaglandenMixin
from ztc.datamodel.tests.factories import (
    FormulierFactory, InformatieObjectType, ZaakInformatieobjectTypeFactory,
    ZaakTypeFactory, ZaakTypenRelatieFactory
)

from .base import ClientAPITestMixin


@freeze_time('2018-02-07')  # datum_begin_geldigheid will be 'today': 'V20180207'
class ZaakTypeAPITests(ClientAPITestMixin, HaaglandenMixin, TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.zaaktype_list_url = reverse('api:zaaktype-list', kwargs={
            'version': '1',
            'catalogus_pk': self.catalogus.pk,
        })
        self.zaaktype_detail_url = reverse('api:zaaktype-detail', kwargs={
            'version': '1',
            'catalogus_pk': self.catalogus.pk,
            'pk': self.zaaktype.pk,
        })

    def test_get_list(self):
        response = self.api_client.get(self.zaaktype_list_url)
        self.assertEqual(response.status_code, 200)

    def test_get_list_response(self):
        """
        Test the actual content of the response.
        """
        self.zaaktype2 = ZaakTypeFactory.create(
            datum_begin_geldigheid=self.zaaktype.datum_begin_geldigheid,
            maakt_deel_uit_van=self.catalogus,
        )
        self.zaaktype3 = ZaakTypeFactory.create(
            datum_begin_geldigheid=self.zaaktype.datum_begin_geldigheid,
            maakt_deel_uit_van=self.catalogus,
        )
        self.zaaktype4 = ZaakTypeFactory.create(
            datum_begin_geldigheid=self.zaaktype.datum_begin_geldigheid,
            maakt_deel_uit_van=self.catalogus,
        )
        # ghost zaaktype, not related to the one we test
        self.zaaktype5 = ZaakTypeFactory.create(
            datum_begin_geldigheid=self.zaaktype.datum_begin_geldigheid,
            maakt_deel_uit_van=self.catalogus,
        )

        for i in range(2):
            formulier = FormulierFactory.create(
                naam='formulier {}'.format(i),
                link='www.example.com'
            )
            self.zaaktype.formulier.add(formulier)

        # fill the ArrayFields
        self.zaaktype.trefwoord = ['trefwoord 1', 'trefwoord 2']
        self.zaaktype.verantwoordingsrelatie = ['verantwoordingsrelatie']

        # heeftGerelateerd..
        self.relatie = ZaakTypenRelatieFactory.create(
            zaaktype_van=self.zaaktype,
            zaaktype_naar=self.zaaktype2,
            aard_relatie='aard relatie',
        )
        # also create a relation between 4 and 5, to test that this one will not show up under self.zaaktype
        ZaakTypenRelatieFactory.create(
            zaaktype_van=self.zaaktype4,
            zaaktype_naar=self.zaaktype5,
        )

        self.zaaktype.is_deelzaaktype_van.add(self.zaaktype3)
        self.zaaktype.save()

        # Create a relation between StatusType inhoudelijk behandeld and self.zaaktype
        self.iot = InformatieObjectType.objects.first()
        self.ziot = ZaakInformatieobjectTypeFactory.create(
            status_type=self.status_type_inhoudelijk_behandeld,
            zaaktype=self.zaaktype,
            informatie_object_type=self.iot,
            volgnummer=1,
            richting='richting',
        )

        response = self.api_client.get(self.zaaktype_list_url)
        self.assertEqual(response.status_code, 200)

        json_response = response.json()
        results = json_response.pop('results')

        expected = {
            '_links': {
                'self': {
                    'href': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/'.format(self.catalogus.pk)
                }
            },
        }
        self.assertEqual(response.json(), expected)

        #
        # check results
        #
        self.assertEqual(len(results), 5)
        OMSCHRIJVING = 'Vergunningaanvraag regulier behandelen'
        # get the result that we want to check. It does not always have the same index..
        result = None
        for _result in results:
            if _result.get('omschrijving') == OMSCHRIJVING:
                result = _result

        heeftRelevantBesluittype = result.pop('heeftRelevantBesluittype')
        # it is http://testserver/api/v1/catalogussen/1/besluittypen/8/
        self.assertEqual(len(heeftRelevantBesluittype), 4)
        for besluittype in heeftRelevantBesluittype:
            self.assertTrue(besluittype.startswith('http://testserver/api/v1/catalogussen/{}/besluittypen/'.format(
                self.catalogus.pk)))

        # for example http://testserver/api/v1/catalogussen/2/zaaktypen/2/eigenschappen/3/
        heeftEigenschap = result.pop('heeftEigenschap')
        self.assertEqual(len(heeftEigenschap), 2)
        for eigenschap in heeftEigenschap:
            self.assertTrue(eigenschap.startswith('http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/eigenschappen/'.format(
                self.catalogus.pk, self.zaaktype.pk)))

        heeftRelevantZaakObjecttype = result.pop('heeftRelevantZaakObjecttype')
        self.assertEqual(len(heeftRelevantZaakObjecttype), 3)
        for zot in heeftRelevantZaakObjecttype:
            self.assertTrue(zot.startswith('http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/'.format(
                self.catalogus.pk)))

        heeftRoltype = result.pop('heeftRoltype')
        self.assertEqual(len(heeftRoltype), 7)
        for roltype in heeftRoltype:
            self.assertTrue(roltype.startswith('http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/roltypen/'.format(
                self.catalogus.pk, self.zaaktype.pk)))

        expected_result = {
            'url': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                self.catalogus.pk, self.zaaktype.pk),
            'versiedatum': '',
            'ingangsdatumObject': 'V20180207',
            'einddatumObject': None,
            'maaktDeelUitVan': 'http://testserver/api/v1/catalogussen/{}/'.format(
                self.catalogus.pk),
            'omschrijving': OMSCHRIJVING,
            'heeftGerelateerd': [
                'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/heeft_gerelateerd/{}/'.format(
                    self.catalogus.pk, self.zaaktype.pk, self.relatie.pk)
            ],
            'verlengingmogelijk': 'J',
            'doorlooptijd': 8,
            'aanleiding': 'De gemeente als bevoegd gezag heeft een aanvraag voor een\n                omgevingsvergunning of milieuwetgeving-gerelateerde vergunning\n                ontvangen.\n                De gemeente heeft geconstateerd dat het een enkelvoudige aanvraag\n                betreft met alleen een milieu-component of dat het een meervoudige\n                aanvraag betreft met betrekking tot een milieuvergunningplichtige\n                inrichting of -locatie en met een milieu-component (milieu-aspect is\n                ‘zwaartepunt’) .\n                De gemeente heeft de ODH gemandateerd om dergelijke aanvragen te\n                behandelen. Zij draagt de ODH op om de ontvangen aanvraag te\n                behandelen. De ODH heeft vastgesteld dat de aanvraag in een reguliere\n                procedure behandeld kan worden.\n                of:\n                De provincie als bevoegd gezag heeft een aanvraag voor een\n                omgevingsvergunning of milieuwetgevinggerelateerde vergunning\n      ',
            'indicatieInternOfExtern': '',
            'verantwoordingsrelatie': ['verantwoordingsrelatie'],
            'handelingInitiator': 'Aanvragen',
            'servicenorm': None,
            'handelingBehandelaar': '',
            'bronzaaktype': None,
            'identificatie': self.zaaktype.zaaktype_identificatie,
            'broncatalogus': None,
            'doel': 'Een besluit nemen op een aanvraag voor een vergunning, ontheffing of\n                vergelijkbare beschikking op basis van een gedegen beoordeling van die\n                aanvraag in een reguliere procedure.',
            'isDeelzaaktypeVan': ['http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                self.catalogus.pk, self.zaaktype3.pk)],
            'omschrijvingGeneriek': None,
            'verlengingstermijn': 30,
            'archiefclassificatiecode': None,
            'vertrouwelijkheidAanduiding': 'OPENBAAR',
            'trefwoord': ['trefwoord 1', 'trefwoord 2'],
            'formulier': [
                {'link': 'www.example.com',
                 'naam': 'formulier 0'},
                {'link': 'www.example.com',
                 'naam': 'formulier 1'}],
            'referentieproces': {
                'naam': str(self.zaaktype.referentieproces),
                'link': None
            },
            'toelichting': 'Bij dit zaaktype draagt het bevoegd gezag de behandeling van de\n                vergunningaanvraag op aan de ODH. De start van de zaakbehandeling\n                verschilt naar gelang de aanvraag ontvangen is door de gemeente dan\n                wel de provincie als bevoegd gezag. Aangezien de gemeente de front-\n                office vormt (in het geval zij bevoegd gezag is), verzorgt zij haar deel van\n                de intake, met name registratie van de zaak en uitdoen van de ontvangst-\n                bevestiging. Daarna zet de ODH als back-office de behandeling voort. Als\n                de provincie het bevoegd gezag is, verzorgt de ODH het front-office en\n                voert de gehele intake uit, waaronder het uitdoen van de ontvangst-\n                bevestiging, en zet daarna als back-office de behandeling voort.\n                De ODH bepaalt tijdens haar intake, of zo spoedig mogelijk daarna, dat de\n                aanvraag in een reguliere procedure behandeld kan worden.',
            'verantwoordelijke': '', 'product_dienst': [{'naam': 'Vergunning voor milieu', 'link': None}],
            'publicatieIndicatie': 'J',
            'zaakcategorie': None,
            'opschortingAanhouding': 'J',
            'publicatietekst': 'N.t.b.',
            'onderwerp': 'Milieu-gerelateerde vergunning',
            'heeftRelevantInformatieobjecttype': [
                'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/heeft_relevant/{}/'.format(
                    self.catalogus.pk, self.zaaktype.pk, self.ziot.pk
                )],
        }
        self.assertEqual(expected_result, result)

    def test_get_list_response_minimum_data(self):
        self.zaaktype.aanleiding = 'aanleiding'
        self.zaaktype.toelichting = 'toelichting'
        self.zaaktype.doel = 'doel'
        self.zaaktype.heeft_relevant_besluittype = []
        self.zaaktype.eigenschap_set.all().delete()
        self.zaaktype.roltype_set.all().delete()
        self.zaaktype.zaakobjecttype_set.all().delete()
        self.zaaktype.save()

        response = self.api_client.get(self.zaaktype_list_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            'results': [
                {
                    'url': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                        self.catalogus.pk, self.zaaktype.pk),
                    'ingangsdatumObject': 'V20180207',
                    'einddatumObject': None,
                    'vertrouwelijkheidAanduiding': 'OPENBAAR',
                    'identificatie': self.zaaktype.zaaktype_identificatie,
                    'product_dienst': [{'naam': 'Vergunning voor milieu', 'link': None}],
                    'broncatalogus': None,
                    'publicatieIndicatie': 'J',
                    'trefwoord': [],
                    'zaakcategorie': None,
                    'toelichting': 'toelichting',
                    'handelingInitiator': 'Aanvragen',
                    'bronzaaktype': None,
                    'aanleiding': 'aanleiding',
                    'verlengingstermijn': 30,
                    'opschortingAanhouding': 'J',
                    'maaktDeelUitVan': 'http://testserver/api/v1/catalogussen/{}/'.format(
                        self.catalogus.pk),
                    'indicatieInternOfExtern': '',
                    'verlengingmogelijk': 'J',
                    'handelingBehandelaar': '',
                    'heeftGerelateerd': [],
                    'doel': 'doel',
                    'versiedatum': '',
                    'formulier': [],
                    'onderwerp': 'Milieu-gerelateerde vergunning',
                    'publicatietekst': 'N.t.b.',
                    'omschrijvingGeneriek': None,
                    'verantwoordingsrelatie': [],
                    'isDeelzaaktypeVan': [],
                    'servicenorm': None,
                    'archiefclassificatiecode': None,
                    'referentieproces': {'naam': str(self.zaaktype.referentieproces.naam), 'link': None},
                    'heeftRelevantBesluittype': [],
                    'doorlooptijd': 8,
                    'verantwoordelijke': '',
                    'omschrijving': 'Vergunningaanvraag regulier behandelen',
                    'heeftEigenschap': [],
                    'heeftRelevantZaakObjecttype': [],
                    'heeftRoltype': [],
                    'heeftRelevantInformatieobjecttype': [],
                }
            ],
            '_links': {
                'self': {'href': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/'.format(
                    self.catalogus.pk)}
            }
        }
        self.assertEqual(response.json(), expected)

    def test_get_detail(self):
        response = self.api_client.get(self.zaaktype_detail_url)
        self.assertEqual(response.status_code, 200)

        result = response.json()

        heeftRelevantBesluittype = result.pop('heeftRelevantBesluittype')
        # it is http://testserver/api/v1/catalogussen/1/besluittypen/8/
        self.assertEqual(len(heeftRelevantBesluittype), 4)
        for besluittype in heeftRelevantBesluittype:
            self.assertTrue(besluittype.startswith(
                'http://testserver/api/v1/catalogussen/{}/besluittypen/'.format(
                    self.catalogus.pk)))

        heeftEigenschap = result.pop('heeftEigenschap')
        self.assertEqual(len(heeftEigenschap), 2)
        for eigenschap in heeftEigenschap:
            self.assertTrue(eigenschap.startswith('http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/eigenschappen/'.format(
                self.catalogus.pk, self.zaaktype.pk)))

        heeftRelevantZaakObjecttype = result.pop('heeftRelevantZaakObjecttype')
        self.assertEqual(len(heeftRelevantZaakObjecttype), 3)
        for zot in heeftRelevantZaakObjecttype:
            self.assertTrue(zot.startswith('http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/'.format(
                self.catalogus.pk)))

        heeftRoltype = result.pop('heeftRoltype')
        self.assertEqual(len(heeftRoltype), 7)
        for roltype in heeftRoltype:
            self.assertTrue(roltype.startswith('http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/roltypen/'.format(
                self.catalogus.pk, self.zaaktype.pk)))

        expected = {
                    'url': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                        self.catalogus.pk, self.zaaktype.pk),
                    'ingangsdatumObject': 'V20180207',
                    'einddatumObject': None,
                    'vertrouwelijkheidAanduiding': 'OPENBAAR',
                    'identificatie': self.zaaktype.zaaktype_identificatie,
                    'product_dienst': [{'naam': 'Vergunning voor milieu', 'link': None}],
                    'broncatalogus': None,
                    'publicatieIndicatie': 'J',
                    'trefwoord': [],
                    'zaakcategorie': None,
                    'toelichting': self.zaaktype.toelichting,
                    'handelingInitiator': 'Aanvragen',
                    'bronzaaktype': None,
                    'aanleiding': self.zaaktype.aanleiding,
                    'verlengingstermijn': 30,
                    'opschortingAanhouding': 'J',
                    'maaktDeelUitVan': 'http://testserver/api/v1/catalogussen/{}/'.format(
                        self.catalogus.pk),
                    'indicatieInternOfExtern': '',
                    'verlengingmogelijk': 'J',
                    'handelingBehandelaar': '',
                    'doel': self.zaaktype.doel,
                    'versiedatum': '',
                    'formulier': [],
                    'onderwerp': 'Milieu-gerelateerde vergunning',
                    'publicatietekst': 'N.t.b.',
                    'omschrijvingGeneriek': None,
                    'verantwoordingsrelatie': [],
                    'isDeelzaaktypeVan': [],
                    'servicenorm': None,
                    'archiefclassificatiecode': None,
                    'referentieproces': {'naam': str(self.zaaktype.referentieproces.naam), 'link': None},
                    'doorlooptijd': 8,
                    'verantwoordelijke': '',
                    'omschrijving': 'Vergunningaanvraag regulier behandelen',
                    'heeftGerelateerd': [],
                    'heeftRelevantInformatieobjecttype': [],
                }
        self.assertEqual(expected, result)


@freeze_time('2018-02-07')  # datum_begin_geldigheid will be 'today': 'V20180207'
class ZaakObjectTypeAPITests(ClientAPITestMixin, HaaglandenMixin, TestCase):
    maxDiff = None

    def setUp(self):
        super().setUp()

        self.zaakobjecttype_list_url = reverse('api:zaakobjecttype-list', kwargs={
            'version': '1',
            'catalogus_pk': self.catalogus.pk,
        })
        self.zaakobjecttype_milieu_detail_url = reverse('api:zaakobjecttype-detail', kwargs={
            'version': '1',
            'catalogus_pk': self.catalogus.pk,
            'pk': self.zaakobjecttype_milieu.pk,
        })

    def test_get_list(self):
        response = self.api_client.get(self.zaakobjecttype_list_url)
        self.assertEqual(response.status_code, 200)

    def test_get_list_response(self):
        response = self.api_client.get(self.zaakobjecttype_list_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            '_links': {
                'self': {
                    'href': 'http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/'.format(
                        self.catalogus.pk)
                }
            },
            'results': [
                {
                    'url': 'http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/{}/'.format(
                        self.catalogus.pk, self.zaakobjecttype_milieu.pk),
                    'relatieOmschrijving': 'De milieu-inrichting(en) en/of milieulocatie(s) waarop de zaak betrekking heeft.',
                    'ingangsdatumObject': 'V20180207',
                    'objecttype': 'Milieu-inrichting of -locatie',
                    'anderObject': 'J',
                    'status_type': None,
                    'einddatumObject': None,
                    'isRelevantVoor': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                        self.catalogus.pk, self.zaaktype.pk),
                }, {
                    'url': 'http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/{}/'.format(
                        self.catalogus.pk, self.zaakobjecttype_pand.pk),
                    'relatieOmschrijving': 'Het (de) pand(en) (in de BAG) waarin het deel van de milieu-inrichting gevestigd',
                    'ingangsdatumObject': 'V20180207',
                    'objecttype': 'PAND',
                    'anderObject': 'N',
                    'status_type': None,
                    'einddatumObject': None,
                    'isRelevantVoor': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                        self.catalogus.pk, self.zaaktype.pk),
                }, {
                    'url': 'http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/{}/'.format(
                        self.catalogus.pk, self.zaakobjecttype_verblijfsobject.pk),
                    'relatieOmschrijving': 'Het (de) verblijfsobject(en) (in de BAG) met bijbehorend adres(sen) waarin het d',
                    'ingangsdatumObject': 'V20180207',
                    'objecttype': 'VERBLIJFSOBJECT',
                    'anderObject': 'N',
                    'status_type': None,
                    'einddatumObject': None,
                    'isRelevantVoor': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                        self.catalogus.pk, self.zaaktype.pk),
                }
            ]
        }
        self.assertEqual(response.json(), expected)

    def test_get_detail(self):
        response = self.api_client.get(self.zaakobjecttype_milieu_detail_url)
        self.assertEqual(response.status_code, 200)

        expected = {
            'anderObject': 'J',
            'einddatumObject': None,
            'ingangsdatumObject': 'V20180207',
            'isRelevantVoor': 'http://testserver/api/v1/catalogussen/{}/zaaktypen/{}/'.format(
                self.catalogus.pk, self.zaaktype.pk),
            'objecttype': 'Milieu-inrichting of -locatie',
            'relatieOmschrijving': 'De milieu-inrichting(en) en/of milieulocatie(s) waarop de zaak betrekking heeft.',
            'status_type': None,
            'url': 'http://testserver/api/v1/catalogussen/{}/zaakobjecttypen/{}/'.format(
                self.catalogus.pk, self.zaakobjecttype_milieu.pk)}
        self.assertEqual(expected, response.json())