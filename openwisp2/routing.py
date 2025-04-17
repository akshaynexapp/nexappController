from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator


routes = []

from openwisp_controller.routing import get_routes as get_controller_routes

routes.extend(get_controller_routes())

from openwisp_network_topology.routing import \
    websocket_urlpatterns as network_topology_routes

routes.extend(network_topology_routes)


application = ProtocolTypeRouter(
    {
        'websocket': AllowedHostsOriginValidator(
            AuthMiddlewareStack(URLRouter(routes))
        )
    }
)
