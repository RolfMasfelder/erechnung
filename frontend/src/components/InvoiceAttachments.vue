<template>
  <BaseCard title="Rechnungsbegründende Dokumente">
    <!-- Upload-Bereich (nur bei draft) -->
    <div
      v-if="isDraft"
      class="upload-area"
      :class="{ 'drag-over': dragOver }"
      @dragover.prevent="dragOver = true"
      @dragleave.prevent="dragOver = false"
      @drop.prevent="handleDrop"
    >
      <div class="upload-content">
        <span class="upload-icon">📎</span>
        <p class="upload-text">
          Dateien hierher ziehen oder
          <label class="file-label">
            <span>auswählen</span>
            <input
              ref="fileInput"
              type="file"
              class="file-input"
              :accept="acceptedTypes"
              multiple
              @change="handleFileSelect"
            />
          </label>
        </p>
        <p class="upload-hint">PDF, PNG, JPEG, CSV, XLSX — max. 10 MB pro Datei</p>
      </div>
    </div>

    <!-- Upload-Formular (sichtbar wenn Dateien ausgewählt) -->
    <div v-if="pendingFiles.length > 0" class="pending-uploads">
      <div v-for="(pf, idx) in pendingFiles" :key="idx" class="pending-file">
        <div class="pending-file-info">
          <span class="pending-file-name">{{ pf.file.name }}</span>
          <span class="pending-file-size">{{ formatFileSize(pf.file.size) }}</span>
        </div>
        <div class="pending-file-fields">
          <div class="field-group">
            <label class="field-label">Beschreibung</label>
            <input
              v-model="pf.description"
              type="text"
              class="field-input"
              placeholder="z. B. Lieferschein Pos. 1"
              maxlength="255"
            />
          </div>
          <div class="field-group">
            <label class="field-label">Dokumenttyp</label>
            <select v-model="pf.attachment_type" class="field-select">
              <option value="supporting_document">Beleg</option>
              <option value="delivery_note">Lieferschein</option>
              <option value="timesheet">Zeitaufstellung</option>
              <option value="other">Sonstiges</option>
            </select>
          </div>
          <button class="remove-btn" title="Entfernen" @click="pendingFiles.splice(idx, 1)">✕</button>
        </div>
        <!-- Fortschrittsbalken -->
        <div v-if="pf.uploading" class="progress-bar">
          <div class="progress-fill" :style="{ width: pf.progress + '%' }"></div>
        </div>
      </div>
      <div class="pending-actions">
        <BaseButton variant="primary" size="sm" :loading="uploading" @click="uploadAll">
          {{ pendingFiles.length === 1 ? 'Hochladen' : `${pendingFiles.length} Dateien hochladen` }}
        </BaseButton>
        <BaseButton variant="secondary" size="sm" :disabled="uploading" @click="pendingFiles = []">
          Abbrechen
        </BaseButton>
      </div>
    </div>

    <!-- Attachment-Liste -->
    <div v-if="attachments.length > 0" class="attachment-list">
      <div v-for="att in attachments" :key="att.id" class="attachment-item">
        <div class="attachment-icon">{{ getIcon(att.mime_type) }}</div>
        <div class="attachment-info">
          <span class="attachment-name">{{ att.original_filename || att.description }}</span>
          <span class="attachment-meta">
            {{ getTypeLabel(att.attachment_type) }} · {{ formatDate(att.uploaded_at) }}
            <span v-if="att.mime_type"> · {{ att.mime_type }}</span>
          </span>
        </div>
        <div class="attachment-actions">
          <button class="action-btn" title="Herunterladen" @click="downloadAttachment(att)">📥</button>
          <button
            v-if="isDraft"
            class="action-btn danger"
            title="Löschen"
            @click="deleteAttachment(att)"
          >🗑️</button>
        </div>
      </div>
    </div>

    <p v-else-if="!loading" class="placeholder">
      Keine Anhänge vorhanden.
    </p>

    <div v-if="loading" class="loading-indicator">Lädt Anhänge...</div>
  </BaseCard>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import BaseCard from '@/components/BaseCard.vue'
import BaseButton from '@/components/BaseButton.vue'
import { attachmentService } from '@/api/services/attachmentService'
import { useToast } from '@/composables/useToast'

const props = defineProps({
  invoiceId: { type: [Number, String], required: true },
  isDraft: { type: Boolean, default: false }
})

const emit = defineEmits(['updated'])

const toast = useToast()
const attachments = ref([])
const loading = ref(false)
const uploading = ref(false)
const dragOver = ref(false)
const fileInput = ref(null)
const pendingFiles = ref([])

const acceptedTypes = '.pdf,.png,.jpg,.jpeg,.csv,.xlsx'
const MAX_SIZE = 10 * 1024 * 1024

const typeLabels = {
  supporting_document: 'Beleg',
  delivery_note: 'Lieferschein',
  timesheet: 'Zeitaufstellung',
  other: 'Sonstiges'
}

const getTypeLabel = (type) => typeLabels[type] || type

const getIcon = (mime) => {
  if (!mime) return '📄'
  if (mime.includes('pdf')) return '📕'
  if (mime.includes('image')) return '🖼️'
  if (mime.includes('csv') || mime.includes('spreadsheet')) return '📊'
  return '📄'
}

const formatFileSize = (bytes) => {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(1) + ' MB'
}

const formatDate = (iso) => {
  if (!iso) return ''
  return new Date(iso).toLocaleDateString('de-DE', {
    day: '2-digit', month: '2-digit', year: 'numeric', hour: '2-digit', minute: '2-digit'
  })
}

const loadAttachments = async () => {
  loading.value = true
  try {
    const data = await attachmentService.getByInvoice(props.invoiceId)
    attachments.value = data.results || data
  } catch (err) {
    console.error('Failed to load attachments:', err)
  } finally {
    loading.value = false
  }
}

const validateFile = (file) => {
  if (file.size > MAX_SIZE) {
    toast.error(`"${file.name}" ist zu groß (max. 10 MB)`)
    return false
  }
  const ext = file.name.split('.').pop().toLowerCase()
  const allowed = ['pdf', 'png', 'jpg', 'jpeg', 'csv', 'xlsx']
  if (!allowed.includes(ext)) {
    toast.error(`"${file.name}" hat einen nicht erlaubten Dateityp`)
    return false
  }
  return true
}

const addFiles = (files) => {
  for (const file of files) {
    if (validateFile(file)) {
      pendingFiles.value.push({
        file,
        description: file.name.replace(/\.[^.]+$/, ''),
        attachment_type: 'supporting_document',
        uploading: false,
        progress: 0
      })
    }
  }
}

const handleDrop = (e) => {
  dragOver.value = false
  if (e.dataTransfer?.files) addFiles(e.dataTransfer.files)
}

const handleFileSelect = (e) => {
  if (e.target.files) addFiles(e.target.files)
  e.target.value = ''
}

const uploadAll = async () => {
  uploading.value = true
  let successCount = 0
  for (const pf of pendingFiles.value) {
    pf.uploading = true
    try {
      await attachmentService.upload(
        props.invoiceId,
        pf.file,
        { description: pf.description, attachment_type: pf.attachment_type },
        (progress) => { pf.progress = progress }
      )
      pf.progress = 100
      successCount++
    } catch (err) {
      console.error('Upload failed:', err)
      toast.error(`Fehler beim Hochladen von "${pf.file.name}"`)
      pf.uploading = false
    }
  }
  if (successCount > 0) {
    toast.success(
      successCount === 1
        ? 'Datei erfolgreich hochgeladen'
        : `${successCount} Dateien erfolgreich hochgeladen`
    )
    pendingFiles.value = pendingFiles.value.filter((pf) => pf.progress < 100)
    await loadAttachments()
    emit('updated')
  }
  uploading.value = false
}

const downloadAttachment = async (att) => {
  try {
    const blob = await attachmentService.download(att)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = att.original_filename || att.description || 'attachment'
    document.body.appendChild(a)
    a.click()
    a.remove()
    URL.revokeObjectURL(url)
  } catch (err) {
    console.error('Download failed:', err)
    toast.error('Fehler beim Herunterladen')
  }
}

const deleteAttachment = async (att) => {
  const name = att.original_filename || att.description
  if (!confirm(`Anhang "${name}" wirklich löschen?`)) return
  try {
    await attachmentService.delete(att.id)
    toast.success('Anhang gelöscht')
    await loadAttachments()
    emit('updated')
  } catch (err) {
    console.error('Delete failed:', err)
    toast.error('Fehler beim Löschen')
  }
}

onMounted(loadAttachments)

defineExpose({ reload: loadAttachments })
</script>

<style scoped>
.upload-area {
  border: 2px dashed #d1d5db;
  border-radius: 0.5rem;
  padding: 1.5rem;
  text-align: center;
  transition: all 0.2s;
  cursor: pointer;
  margin-bottom: 1rem;
}

.upload-area.drag-over {
  border-color: #3b82f6;
  background-color: #eff6ff;
}

.upload-content {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
}

.upload-icon {
  font-size: 2rem;
}

.upload-text {
  margin: 0;
  color: #374151;
  font-size: 0.95rem;
}

.file-label {
  color: #3b82f6;
  cursor: pointer;
  text-decoration: underline;
}

.file-input {
  display: none;
}

.upload-hint {
  margin: 0;
  font-size: 0.8rem;
  color: #9ca3af;
}

/* Pending uploads */
.pending-uploads {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
  margin-bottom: 1rem;
  padding: 1rem;
  background: #f9fafb;
  border-radius: 0.5rem;
}

.pending-file {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.pending-file-info {
  display: flex;
  justify-content: space-between;
  font-size: 0.875rem;
}

.pending-file-name {
  font-weight: 500;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  max-width: 300px;
}

.pending-file-size {
  color: #6b7280;
}

.pending-file-fields {
  display: flex;
  gap: 0.5rem;
  align-items: flex-end;
}

.field-group {
  display: flex;
  flex-direction: column;
  gap: 0.2rem;
  flex: 1;
}

.field-group:last-of-type {
  flex: 0 0 auto;
}

.field-label {
  font-size: 0.72rem;
  font-weight: 600;
  color: #374151;
  text-transform: uppercase;
  letter-spacing: 0.03em;
}

.field-input {
  width: 100%;
  padding: 0.375rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #111827;
  background: #ffffff;
  box-sizing: border-box;
}

.field-input::placeholder {
  color: #9ca3af;
}

.field-select {
  width: 100%;
  padding: 0.375rem 0.5rem;
  border: 1px solid #d1d5db;
  border-radius: 0.25rem;
  font-size: 0.875rem;
  color: #111827;
  background: #ffffff;
  box-sizing: border-box;
}

.remove-btn {
  background: none;
  border: none;
  color: #9ca3af;
  cursor: pointer;
  font-size: 1rem;
  padding: 0.25rem;
}

.remove-btn:hover {
  color: #ef4444;
}

.progress-bar {
  height: 4px;
  background: #e5e7eb;
  border-radius: 2px;
  overflow: hidden;
}

.progress-fill {
  height: 100%;
  background: #3b82f6;
  transition: width 0.3s;
}

.pending-actions {
  display: flex;
  gap: 0.5rem;
  margin-top: 0.25rem;
}

/* Attachment list */
.attachment-list {
  display: flex;
  flex-direction: column;
}

.attachment-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem 0;
  border-bottom: 1px solid #f3f4f6;
}

.attachment-item:last-child {
  border-bottom: none;
}

.attachment-icon {
  font-size: 1.5rem;
  flex-shrink: 0;
}

.attachment-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 0.125rem;
}

.attachment-name {
  font-size: 0.95rem;
  font-weight: 500;
  color: #111827;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.attachment-meta {
  font-size: 0.8rem;
  color: #6b7280;
}

.attachment-actions {
  display: flex;
  gap: 0.25rem;
  flex-shrink: 0;
}

.action-btn {
  background: none;
  border: none;
  cursor: pointer;
  font-size: 1.1rem;
  padding: 0.25rem 0.5rem;
  border-radius: 0.25rem;
  transition: background 0.15s;
}

.action-btn:hover {
  background: #f3f4f6;
}

.action-btn.danger:hover {
  background: #fee2e2;
}

.placeholder {
  text-align: center;
  color: #6b7280;
  padding: 1rem;
}

.loading-indicator {
  text-align: center;
  color: #6b7280;
  padding: 1rem;
}

@media (max-width: 640px) {
  .pending-file-fields {
    flex-direction: column;
  }

  .field-input,
  .field-select {
    width: 100%;
  }
}
</style>
