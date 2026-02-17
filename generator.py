"""
Document generation service
Handles template-based document creation
"""

import os
import tempfile
from pathlib import Path
from templates import get_template_manager


class DocumentGenerator:
    """Generates lab sheet documents."""
    
    def __init__(self, output_dir=None):
        """Initialize generator."""
        self.template_manager = get_template_manager()
        self.output_dir = output_dir or tempfile.gettempdir()
        
        # Ensure output directory exists
        Path(self.output_dir).mkdir(parents=True, exist_ok=True)
    
    def generate(self, user, module, schedule, logo_path=None):
        """
        Generate lab sheet document.
        
        Args:
            user: User object
            module: Module object
            schedule: Schedule object
            logo_path: Optional path to logo
            
        Returns:
            Path to generated document
        """
        # Get template
        template = self.template_manager.get_template(module.template)
        
        # Determine sheet type
        sheet_type = module.sheet_type
        if sheet_type == 'Custom' and module.custom_sheet_type:
            sheet_type = module.custom_sheet_type
        
        # Format practical number
        practical_num = schedule.current_practical_number
        if schedule.use_zero_padding:
            sheet_label = f"{sheet_type} {practical_num:02d}"
        else:
            sheet_label = f"{sheet_type} {practical_num}"
        
        # Change to output directory
        original_dir = os.getcwd()
        os.chdir(self.output_dir)
        
        try:
            # Generate document
            filename = template.generate(
                student_name=user.name,
                student_id=user.student_id,
                module_name=module.name,
                module_code=module.code,
                sheet_label=sheet_label,
                logo_path=logo_path
            )
            
            # Get full path
            full_path = os.path.join(self.output_dir, filename)
            
            return full_path
            
        finally:
            # Restore original directory
            os.chdir(original_dir)
    
    def generate_from_data(self, student_name, student_id, module_name, 
                          module_code, sheet_type, practical_number, 
                          template_id='classic', use_zero_padding=True, 
                          logo_path=None):
        """
        Generate document from raw data (for API calls).
        
        Args:
            student_name: Student's name
            student_id: Student ID
            module_name: Module name
            module_code: Module code
            sheet_type: Type of sheet (Practical, Lab, etc.)
            practical_number: Number of practical
            template_id: Template to use
            use_zero_padding: Whether to pad numbers (01 vs 1)
            logo_path: Optional logo path
            
        Returns:
            Path to generated document
        """
        # Get template
        template = self.template_manager.get_template(template_id)
        
        # Format sheet label
        if use_zero_padding:
            sheet_label = f"{sheet_type} {practical_number:02d}"
        else:
            sheet_label = f"{sheet_type} {practical_number}"
        
        # Change to output directory
        original_dir = os.getcwd()
        os.chdir(self.output_dir)
        
        try:
            # Generate document
            filename = template.generate(
                student_name=student_name,
                student_id=student_id,
                module_name=module_name,
                module_code=module_code,
                sheet_label=sheet_label,
                logo_path=logo_path
            )
            
            # Get full path
            full_path = os.path.join(self.output_dir, filename)
            
            return full_path
            
        finally:
            # Restore original directory
            os.chdir(original_dir)


# Singleton instance
_document_generator = None

def get_document_generator():
    """Get document generator singleton."""
    global _document_generator
    if _document_generator is None:
        output_dir = os.path.join(tempfile.gettempdir(), 'labsheets')
        _document_generator = DocumentGenerator(output_dir)
    return _document_generator
