import logging

from swapper import swappable_setting

from .base.models import (
    AbstractNas,
    AbstractOrganizationRadiusSettings,
    AbstractPhoneToken,
    AbstractRadiusAccounting,
    AbstractRadiusBatch,
    AbstractRadiusCheck,
    AbstractRadiusGroup,
    AbstractRadiusGroupCheck,
    AbstractRadiusGroupReply,
    AbstractRadiusPostAuth,
    AbstractRadiusReply,
    AbstractRadiusToken,
    AbstractRadiusUserGroup,
    AbstractRegisteredUser,
)

logger = logging.getLogger(__name__)


class RadiusCheck(AbstractRadiusCheck):
    class Meta(AbstractRadiusCheck.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusCheck')
        # db_table = 'openwisp_radius_radiuscheck'


class RadiusReply(AbstractRadiusReply):
    class Meta(AbstractRadiusReply.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusReply')
        # db_table = 'openwisp_radius_radiusreply'    

class RadiusAccounting(AbstractRadiusAccounting):
    class Meta(AbstractRadiusAccounting.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusAccounting')
        # db_table = 'openwisp_radius_radiusaccounting'

class RadiusGroup(AbstractRadiusGroup):
    class Meta(AbstractRadiusGroup.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusGroup')
        db_table = 'openwisp_radius_radiusgroup'


class RadiusGroupCheck(AbstractRadiusGroupCheck):
    class Meta(AbstractRadiusGroupCheck.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusGroupCheck')
        # db_table = 'openwisp_radius_radiusgroupcheck'

class RadiusGroupReply(AbstractRadiusGroupReply):
    class Meta(AbstractRadiusGroupReply.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusGroupReply')
        # db_table = 'openwisp_radius_radiusgroupreply'

class RadiusUserGroup(AbstractRadiusUserGroup):
    class Meta(AbstractRadiusUserGroup.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusUserGroup')
        # db_table = 'openwisp_radius_radiususergroup'

class RadiusPostAuth(AbstractRadiusPostAuth):
    class Meta(AbstractRadiusPostAuth.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusPostAuth')
        # db_table = 'openwisp_radius_radiuspostauth'

class Nas(AbstractNas):
    class Meta(AbstractNas.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'Nas')
        # db_table = 'openwisp_radius_nas'

class RadiusBatch(AbstractRadiusBatch):
    class Meta(AbstractRadiusBatch.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusBatch')
        # db_table = 'openwisp_radius_radiusbatch'

class RadiusToken(AbstractRadiusToken):
    class Meta(AbstractRadiusToken.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RadiusToken')
        db_table = 'openwisp_radius_radiustoken'

class OrganizationRadiusSettings(AbstractOrganizationRadiusSettings):
    class Meta(AbstractOrganizationRadiusSettings.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'OrganizationRadiusSettings')
        # db_table = 'openwisp_radius_organizationradiussettings'

class PhoneToken(AbstractPhoneToken):
    class Meta(AbstractPhoneToken.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'PhoneToken')
        # db_table = 'openwisp_radius_phonetoken'


class RegisteredUser(AbstractRegisteredUser):
    class Meta(AbstractRegisteredUser.Meta):
        abstract = False
        swappable = swappable_setting('nexapp_radius', 'RegisteredUser')
        # db_table = 'openwisp_radius_registereduser'