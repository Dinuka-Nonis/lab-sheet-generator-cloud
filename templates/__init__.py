"""
Template manager for cloud service
Includes Classic and SLIIT templates
"""

from .classic import ClassicTemplate
from .sliit import SLIITTemplate


class TemplateManager:
    """Manages document templates."""
    
    def __init__(self):
        self.templates = {
            'classic': ClassicTemplate(),
            'sliit': SLIITTemplate()
        }
    
    def get_template(self, template_id='classic'):
        """Get template by ID."""
        return self.templates.get(template_id, self.templates['classic'])
    
    def list_templates(self):
        """List available templates."""
        return [
            {
                'id': tid,
                'name': template.template_name
            }
            for tid, template in self.templates.items()
        ]


# Singleton instance
_template_manager = None

def get_template_manager():
    """Get template manager singleton."""
    global _template_manager
    if _template_manager is None:
        _template_manager = TemplateManager()
    return _template_manager
