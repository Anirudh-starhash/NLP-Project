// pdf-properties.component.ts
import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';
import { MatDialog } from '@angular/material/dialog';
import { PdfService } from '../../services/pdf.service';
import { EmbeddingDialogComponent } from '../embedding-dialog/embedding-dialog.component';

@Component({
  selector: 'app-pdf-prop',
  standalone: true,
  imports: [CommonModule, EmbeddingDialogComponent],
  templateUrl: './pdfprop.component.html',
  styleUrls: ['./pdfprop.component.css']
})
export class PdfPropComponent implements OnInit {
  @Input() fileId!: number;  // passed from parent
  @Input() fileName!: string;
  @Output() back = new EventEmitter<void>();

  chunks: any[] = [];
  loading = true;

  constructor(
    private httpClient: HttpClient,
    public dialog: MatDialog,
    private pdfService:PdfService) {}

  ngOnInit() {
    this.fetchChunks();
  }

  fetchChunks() {
    const token = localStorage.getItem('access_token');

    this.httpClient.get(`http://localhost:5000/api/get_chunks/${this.fileId}`, {

      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (res: any) => {
        this.chunks = res.chunks;
        this.loading = false;
      },
      error: (err) => {
        console.error("Error fetching chunks:", err);
        this.loading = false;
      }
    });
  }


  showEmbedding(embeddingId: number): void {
      if (!embeddingId) {
        console.warn('No embedding ID provided for this chunk.');
        return;
      }

      // Call the service to fetch the embedding data
      this.pdfService.getEmbedding(embeddingId).subscribe({
        next: (embeddingData) => {
          // On success, open the dialog and pass the data
          this.dialog.open(EmbeddingDialogComponent, {
            width: '600px',
            data: embeddingData // This data is received by the dialog component
          });
        },
        error: (err) => {
          console.error('Failed to fetch embedding:', err);
          // Optionally show a user-friendly error (e.g., with a toast/snackbar)
          alert('Could not load the embedding.');
        }
      });
  }

  goBack() {
    this.back.emit();
  }
}
