import translators.base_translator


class WorkspaceTranslator(translators.base_translator.BaseTranslator):
    """Translates an AWS Workspace to an IT Glue Configuration with an
    IT Glue Configuration Interface
    """
    FIELDS = [
        'name',
        'configuration_status_id',
        'notes',
        'ip_address',
        'ip_notes'
    ]

    def _name(self):
        return self.data.get('WorkspaceId') or 'Unnamed Workspace'

    def _configuration_status_id(self):
        state_name = self.data.get('State')
        active_status_id = self.options.get('active_status_id')
        inactive_status_id = self.options.get('inactive_status_id')
        if not active_status_id or not inactive_status_id:
            raise self.TranslatorError('Both an active_status_id and an inactive_status_id must be provided')
        if state_name.lower() == 'available':
            return active_status_id
        else:
            return inactive_status_id

    def _notes(self):
        workspace_props = self.data.get('WorkspaceProperties')
        notes_dict = {
            'workspace_id': self.data.get('WorkspaceId'),
            'computer_name': self.data.get('Computername'),
            'compute_type': workspace_props.get('ComputeTypeName'),
            'bundle_id': self.data.get('BundleId'),
            'subnet_id': self.data.get('SubnetId'),
            'directory_id': self.data.get('DirectoryId'),
            'error_code': self.data.get('ErrorCode'),
            'error_message': self.data.get('ErrorMessage'),
            'root_volume_size_gib': workspace_props.get('RootVolumeSizeGib'),
            'running_mode': workspace_props.get('RunningMode'),
            'running_mode_auto_stop_timeout_in_min': workspace_props.get('RunningModeAutoStopTimeoutInMinutes'),
            'user_volume_size_gib': workspace_props.get('UserVolumeSizeGib')
        }
        return self._format_notes(notes_dict)

    def _ip_address(self):
        return self.data.get('IpAddress', '')

    def _ip_notes(self):
        return self._format_notes({'subnet_id': self.data.get('SubnetId')})
