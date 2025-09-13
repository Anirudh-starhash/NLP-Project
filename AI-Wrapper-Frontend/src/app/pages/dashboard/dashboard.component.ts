import { HttpClient } from '@angular/common/http';
import { Component, OnInit } from '@angular/core';
import { CommonModule } from '@angular/common';

@Component({
  selector: 'app-dashboard',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './dashboard.component.html',
  styleUrls: ['./dashboard.component.css']
})
export class DashboardComponent implements OnInit {
  isSidebarOpen = true;
  isDragging = false;
  fileName: string | null = null;
  uploadedPdfs: any[] = [];
  itemsPerPage = 5;
  currentPage = 0;

  constructor(private httpClient: HttpClient) {}

  ngOnInit() {
    this.fetchUploadedPdfs();
  }

  // Get current page items
   // Get current page items
  paginatedPdfs() {
    const start = this.currentPage * this.itemsPerPage;
    const end = start + this.itemsPerPage;
    return this.uploadedPdfs.slice(start, end);
  }

  // Generate page numbers
  pageNumbers() {
    const pages = Math.ceil(this.uploadedPdfs.length / this.itemsPerPage);
    let pageLabels = [];
    for (let i = 0; i < pages; i++) {
      const start = i * this.itemsPerPage + 1;
      const end = Math.min((i + 1) * this.itemsPerPage, this.uploadedPdfs.length);
      pageLabels.push(`${start}-${end}`);
    }
    return pageLabels;
  }

  // In your component.ts
  getDisplayName(filename: string): string {

    const parts = filename.split('_');
    if (parts.length > 1 && /^[0-9a-fA-F-]{36}$/.test(parts[0])) {
      parts.shift();
    }
    return parts.join('_'); // Join the rest back
  }

  goToPage(index: number) {
    this.currentPage = index;
  }

  toggleSidebar() {
    this.isSidebarOpen = !this.isSidebarOpen;
  }

  onDragOver(event: DragEvent) {
    event.preventDefault();
    this.isDragging = true;
  }

  onDragLeave(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
  }

  onDrop(event: DragEvent) {
    event.preventDefault();
    this.isDragging = false;
    const files = event.dataTransfer?.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  onFileSelected(event: Event) {
    const element = event.currentTarget as HTMLInputElement;
    const files = element.files;
    if (files && files.length > 0) {
      this.handleFile(files[0]);
    }
  }

  uploadFile(file: File) {
    const token = localStorage.getItem('access_token');
    const formData = new FormData();
    formData.append('file', file);

    this.httpClient.post('http://localhost:5000/api/upload_pdf', formData, {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        console.log('Upload successful', response);
        alert('File uploaded successfully!');
        this.fetchUploadedPdfs(); // refresh list
      },
      error: (error) => {
        console.error('Upload error', error);
        alert('Failed to upload file.');
      }
    });
  }


  fetchUploadedPdfs() {
    const token = localStorage.getItem('access_token'); // get the stored token

    this.httpClient.get('http://localhost:5000/api/get_pdfs', {
      headers: {
        'Authorization': `Bearer ${token}`
      },
      withCredentials: true
    }).subscribe({
      next: (response: any) => {
        this.uploadedPdfs = response.pdfs.map((pdf: any) => ({
          ...pdf,
          upload_time: new Date(pdf.upload_time + 'Z').toLocaleString() // Convert to local timezone
        }));
      },
      error: (error) => {
        console.error('Error fetching PDFs', error);
      }
    });
  }


  private handleFile(file: File) {
    if (file.type !== "application/pdf") {
      alert('Please select a valid PDF file.');
      this.fileName = null;
      return;
    }

    const originalName = file.name;

    // Check if a PDF with the same display name already exists
    const duplicate = this.uploadedPdfs.some(pdf =>
      this.getDisplayName(pdf.filename) === originalName
    );

    if (duplicate) {
      alert(`A PDF with the name "${originalName}" already exists. Upload discarded.`);
      this.fileName = null;
      return; // Stop further processing
    }

    console.log('PDF File selected:', file);
    this.fileName = file.name;
    this.uploadFile(file);
  }
}
