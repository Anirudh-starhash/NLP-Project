// pdf-properties.component.ts
import { Component, Input, Output, EventEmitter, OnInit } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-pdf-prop',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './pdfprop.component.html',
  styleUrls: ['./pdfprop.component.css']
})
export class PdfPropComponent implements OnInit {
  @Input() fileId!: number;  // passed from parent
  @Input() fileName!: string;
  @Output() back = new EventEmitter<void>();

  chunks: any[] = [];
  loading = true;

  constructor(private httpClient: HttpClient) {}

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

  goBack() {
    this.back.emit();
  }
}
