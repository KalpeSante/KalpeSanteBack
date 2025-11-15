"""
KALPÉ SANTÉ - Core Serializers
Base serializers providing common functionality.
"""

from rest_framework import serializers
from django.utils.translation import gettext_lazy as _


class BaseSerializer(serializers.ModelSerializer):
    """
    Base serializer with common configuration for all models.
    """
    
    class Meta:
        abstract = True
    
    def to_representation(self, instance):
        """
        Customize representation to exclude soft-deleted items.
        """
        representation = super().to_representation(instance)
        
        # Convert UUID to string for consistency
        if 'id' in representation:
            representation['id'] = str(representation['id'])
        
        return representation


class TimestampedSerializer(serializers.Serializer):
    """
    Mixin serializer for timestamped fields (read-only).
    """
    created_at = serializers.DateTimeField(read_only=True)
    updated_at = serializers.DateTimeField(read_only=True)


class AuditLogSerializer(serializers.Serializer):
    """
    Serializer for audit log display (read-only).
    """
    id = serializers.UUIDField(read_only=True)
    user = serializers.StringRelatedField(read_only=True)
    action = serializers.CharField(read_only=True)
    resource_type = serializers.CharField(read_only=True)
    resource_id = serializers.UUIDField(read_only=True)
    ip_address = serializers.IPAddressField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    metadata = serializers.JSONField(read_only=True)




