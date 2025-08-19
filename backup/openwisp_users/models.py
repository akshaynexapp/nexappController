from swapper import swappable_setting
from django.contrib.auth.models import Group as AbstractGroup
from organizations.abstract import (
    AbstractOrganization,
    AbstractOrganizationInvitation,
    AbstractOrganizationOwner,
    AbstractOrganizationUser,
)

from .base.models import (
    AbstractUser,
    BaseGroup,
    BaseOrganization,
    BaseOrganizationOwner,
    BaseOrganizationUser,
)



class User(AbstractUser):
    class Meta(AbstractUser.Meta):
        abstract = False


class Organization(BaseOrganization, AbstractOrganization):
    class Meta(AbstractOrganization.Meta):
        swappable = swappable_setting('nexapp_users', 'Organization')
        # db_table = 'openwisp_users_organization'


class OrganizationUser(BaseOrganizationUser, AbstractOrganizationUser):
    class Meta(AbstractOrganizationUser.Meta):
        swappable =  swappable_setting('nexapp_users', 'OrganizationUser')
        # db_table = 'openwisp_users_organizationuser'


class OrganizationOwner(BaseOrganizationOwner, AbstractOrganizationOwner):
    class Meta(AbstractOrganizationOwner.Meta):
        swappable =  swappable_setting('nexapp_users', 'OrganizationOwner')
        # db_table = 'openwisp_users_organizationowner'


# only needed for compatibility with django-organizations~=2.x
# it is not direclty used in OpenWISP right now but users
# are free to implement it / swap it if needed
# for more information refer to the django-organizations docs:
# https://django-organizations.readthedocs.io/
class OrganizationInvitation(AbstractOrganizationInvitation):
    class Meta(AbstractOrganizationInvitation.Meta):
        swappable = swappable_setting('nexapp_users', 'OrganizationInvitation')


class Group(BaseGroup, AbstractGroup):
    class Meta(BaseGroup.Meta):
        swappable = swappable_setting('nexapp_users', 'Group')
