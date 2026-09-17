/* Berkas Panitia A - JavaScript sendiri, tanpa pustaka luar. */
(function () {
  "use strict";

  /* ---------------- tab ---------------- */
  /* Satu bilah tab per halaman. Peran ARIA dipasang di sini supaya penanda di
     web.py tetap ringkas, lengkap dengan panah kiri/kanan dan ingatan per
     halaman. Tab yang memuat sasaran #hash menang atas ingatan itu. */
  function pasangTab() {
    document.querySelectorAll('.tab[role="tablist"]').forEach(function (tab) {
      var tombol = Array.prototype.slice.call(tab.querySelectorAll("button[data-panel]"));
      var panel = tombol.map(function (b) { return document.getElementById(b.dataset.panel); });
      var kunci = "tab-" + (tab.dataset.tab || location.pathname);

      panel.forEach(function (p, i) {
        if (!p) return;
        p.setAttribute("role", "tabpanel");
        p.setAttribute("aria-labelledby", tombol[i].id);
        p.setAttribute("tabindex", "0");
      });

      function pilih(b, fokus) {
        tombol.forEach(function (x, i) {
          var aktif = x === b;
          x.classList.toggle("aktif", aktif);
          x.setAttribute("aria-selected", aktif ? "true" : "false");
          x.tabIndex = aktif ? 0 : -1;
          if (panel[i]) panel[i].classList.toggle("aktif", aktif);
        });
        if (fokus) b.focus();
        try { localStorage.setItem(kunci, b.dataset.panel); } catch (e) {}
      }

      tab.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-panel]");
        if (b) pilih(b);
      });

      tab.addEventListener("keydown", function (ev) {
        var i = tombol.indexOf(document.activeElement);
        if (i < 0) return;
        var tujuan = { ArrowRight: i + 1, ArrowLeft: i - 1,
                       Home: 0, End: tombol.length - 1 }[ev.key];
        if (tujuan === undefined) return;
        ev.preventDefault();
        pilih(tombol[(tujuan + tombol.length) % tombol.length], true);
      });

      var awal = null;
      if (location.hash) {
        var sasaran = document.querySelector(location.hash);
        var induk = sasaran && sasaran.closest(".panel");
        if (induk) awal = tab.querySelector('button[data-panel="' + induk.id + '"]');
      }
      if (!awal) {
        var simpan = null;
        try { simpan = localStorage.getItem(kunci); } catch (e) {}
        awal = simpan && tab.querySelector('button[data-panel="' + simpan + '"]');
      }
      pilih(awal || tombol[0]);
    });
  }

  /* ---------------- baris dinamis ---------------- */
  function nomori(wadah) {
    var i = 1;
    wadah.querySelectorAll(".baris").forEach(function (b) {
      var n = b.querySelector(".no");
      if (n) n.textContent = i++;
    });
  }

  function pasangBarisDinamis() {
    document.querySelectorAll("[data-dinamis]").forEach(function (wadah) {
      var contoh = wadah.querySelector("template");

      wadah.addEventListener("click", function (ev) {
        var t = ev.target.closest("button");
        if (!t) return;
        var baris = t.closest(".baris");
        if (t.dataset.aksi === "hapus" && baris) {
          ev.preventDefault();
          baris.remove();
          nomori(wadah);
        } else if (t.dataset.aksi === "naik" && baris && baris.previousElementSibling) {
          ev.preventDefault();
          baris.parentNode.insertBefore(baris, baris.previousElementSibling);
          nomori(wadah);
        } else if (t.dataset.aksi === "turun" && baris && baris.nextElementSibling) {
          ev.preventDefault();
          baris.parentNode.insertBefore(baris.nextElementSibling, baris);
          nomori(wadah);
        }
      });

      var tambah = document.querySelector('[data-tambah="' + wadah.dataset.dinamis + '"]');
      if (tambah && contoh) {
        tambah.addEventListener("click", function (ev) {
          ev.preventDefault();
          var isi = document.importNode(contoh.content, true);
          wadah.appendChild(isi);
          nomori(wadah);
          var baru = wadah.lastElementChild.querySelector("input,textarea,select");
          if (baru) baru.focus();
        });
      }
      nomori(wadah);
    });
  }

  /* ------------- desa mengikuti kecamatan ------------- */
  function pasangWilayah() {
    var kec = document.getElementById("f_kecamatan");
    var desa = document.getElementById("f_desa");
    if (!kec || !desa || !window.DAFTAR_DESA) return;

    function isi() {
      var terpilih = desa.dataset.terpilih || desa.value;
      var pilihan = window.DAFTAR_DESA.filter(function (d) {
        return !kec.value || String(d.kecamatan_id) === String(kec.value);
      });
      desa.innerHTML = '<option value="">- pilih desa/kelurahan -</option>';
      pilihan.forEach(function (d) {
        var o = document.createElement("option");
        o.value = d.id;
        o.textContent = d.jenis + " " + d.nama + (d.pejabat ? "  (" + d.pejabat + ")" : "");
        if (String(d.id) === String(terpilih)) o.selected = true;
        desa.appendChild(o);
      });
    }
    kec.addEventListener("change", function () { desa.dataset.terpilih = ""; isi(); });
    isi();
  }

  /* ------------- hitung selisih luas langsung ------------- */
  function pasangLuas() {
    var pbt = document.getElementById("f_luas_pbt");
    var surat = document.getElementById("f_luas_surat");
    var hasil = document.getElementById("f_selisih");
    if (!pbt || !surat || !hasil) return;
    function hitung() {
      var a = parseInt(pbt.value || "0", 10), b = parseInt(surat.value || "0", 10);
      if (!pbt.value || !surat.value) { hasil.value = ""; return; }
      var s = a - b;
      hasil.value = (s === 0 ? "tidak ada selisih"
        : (s > 0 ? "+" : "") + s.toLocaleString("id-ID") + " m²");
    }
    pbt.addEventListener("input", hitung);
    surat.addEventListener("input", hitung);
    hitung();
  }

  /* ------------- pencarian tabel di sisi klien ------------- */
  /* Kotak cari dan tab status menyaring tabel yang sama, jadi keduanya
     dihitung sekali dalam terapkan(). */
  function pasangSaring() {
    var kotak = document.getElementById("saring");
    var tapis = document.querySelector(".tab.tapis");
    if (!kotak && !tapis) return;
    var status = "";

    function terapkan() {
      var q = kotak ? kotak.value.toLowerCase().trim() : "";
      var n = 0;
      document.querySelectorAll("tbody tr[data-cari]").forEach(function (tr) {
        var cocok = (!q || tr.dataset.cari.indexOf(q) >= 0) &&
                    (!status || tr.dataset.status === status);
        tr.hidden = !cocok;
        if (cocok) n++;
      });
      var info = document.getElementById("jumlah-tampil");
      if (info) info.textContent = n + " berkas";
      var kosong = document.querySelector(".tak-cocok");
      if (kosong) kosong.hidden = n > 0;
    }

    if (kotak) kotak.addEventListener("input", terapkan);
    if (tapis) {
      tapis.addEventListener("click", function (ev) {
        var b = ev.target.closest("button[data-status]");
        if (!b) return;
        status = b.dataset.status;
        tapis.querySelectorAll("button").forEach(function (x) {
          x.classList.toggle("aktif", x === b);
          x.setAttribute("aria-pressed", x === b ? "true" : "false");
        });
        try { sessionStorage.setItem("tapis-status", status); } catch (e) {}
        terapkan();
      });
      var simpan = "";
      try { simpan = sessionStorage.getItem("tapis-status") || ""; } catch (e) {}
      var awal = tapis.querySelector('button[data-status="' + simpan + '"]') ||
                 tapis.querySelector("button");
      if (awal) awal.click();
    }
    terapkan();
  }

  /* ------------- konfirmasi tindakan ------------- */
  /* Didengarkan di tingkat dokumen supaya tombol pada potongan yang baru
     diambil (kartu lipat) ikut tertangani tanpa dipasangi ulang. */
  function pasangKonfirmasi() {
    document.addEventListener("click", function (ev) {
      var el = ev.target.closest("[data-konfirmasi]");
      if (el && !window.confirm(el.dataset.konfirmasi)) ev.preventDefault();
    });
  }

  /* ------------- kartu lipat, isinya diambil saat dibuka ------------- */
  var KUNCI_LIPAT = "lipat-terbuka";

  function ingatan() {
    try { return JSON.parse(localStorage.getItem(KUNCI_LIPAT) || "[]"); } catch (e) { return []; }
  }

  function ingat(id, buka) {
    var daftar = ingatan().filter(function (x) { return x !== id; });
    if (buka) daftar.push(id);
    try { localStorage.setItem(KUNCI_LIPAT, JSON.stringify(daftar.slice(-12))); } catch (e) {}
  }

  /* Isi kartu diambil sekali saja, saat kartunya pertama kali dibuka. */
  function muatIsi(kartu) {
    if (!kartu || kartu.dataset.terisi === "1") return;
    var kepala = kartu.querySelector(".lipat-kepala");
    var isi = kartu.querySelector(".lipat-isi");
    var alamat = kepala && kepala.getAttribute("data-muat");
    if (!alamat) return;
    kartu.dataset.terisi = "1";
    isi.innerHTML = '<div class="lipat-tunggu"><span class="putar"></span>Memuat…</div>';
    fetch(alamat, { credentials: "same-origin" })
      .then(function (r) {
        if (r.status === 401) throw new Error("sesi");
        /* Tanpa penanda ini yang diterima bukan potongan kartu — jangan disuntikkan. */
        if (!r.ok || !r.headers.get("X-Potongan")) throw new Error(r.status);
        return r.text();
      })
      .then(function (teks) { isi.innerHTML = teks; })
      .catch(function (galat) {
        kartu.dataset.terisi = "";
        isi.innerHTML = galat && galat.message === "sesi"
          ? '<div class="lipat-galat"><span>Sesi sudah habis.</span>' +
            '<a class="btn kecil" href="/masuk">Masuk lagi</a></div>'
          : '<div class="lipat-galat"><span>Isi bagian ini gagal diambil.</span>' +
            '<button type="button" class="btn kecil" data-ulang>Coba lagi</button></div>';
      });
  }

  function setelLipat(kartu, buka, simpan) {
    var kepala = kartu.querySelector(".lipat-kepala");
    var isi = kartu.querySelector(".lipat-isi");
    kartu.classList.toggle("terbuka", buka);
    kepala.setAttribute("aria-expanded", buka ? "true" : "false");
    isi.hidden = !buka;
    if (simpan !== false) ingat(kartu.id, buka);
    if (buka) muatIsi(kartu);
  }

  function pasangLipat() {
    var semua = document.querySelectorAll(".lipat");
    if (!semua.length) return;

    document.addEventListener("click", function (ev) {
      if (ev.button || ev.metaKey || ev.ctrlKey || ev.shiftKey || ev.altKey) return;
      var ulang = ev.target.closest("[data-ulang]");
      if (ulang) { muatIsi(ulang.closest(".lipat")); return; }
      var kepala = ev.target.closest(".lipat-kepala");
      if (!kepala) return;
      ev.preventDefault();
      var kartu = kepala.closest(".lipat");
      setelLipat(kartu, !kartu.classList.contains("terbuka"));
    });

    /* Yang sudah dirakit server dalam keadaan terbuka tak perlu diambil ulang. */
    semua.forEach(function (kartu) {
      if (kartu.classList.contains("terbuka")) {
        kartu.dataset.terisi = "1";
        ingat(kartu.id, true);
      }
    });

    /* Buka lagi bagian yang terakhir dipakai petugas. */
    ingatan().forEach(function (id) {
      var kartu = document.getElementById(id);
      if (kartu && kartu.classList.contains("lipat") && !kartu.classList.contains("terbuka"))
        setelLipat(kartu, true, false);
    });

    var sasaran = location.hash && document.querySelector(location.hash);
    if (sasaran && sasaran.classList && sasaran.classList.contains("lipat")) {
      setelLipat(sasaran, true);
      sasaran.scrollIntoView();
    }
  }

  /* ------------- saring isi satu kartu ------------- */
  function pasangSaringLipat() {
    document.addEventListener("input", function (ev) {
      var kotak = ev.target.closest("input[data-saring]");
      if (!kotak) return;
      var wadah = document.getElementById(kotak.dataset.saring);
      if (!wadah) return;
      var q = kotak.value.toLowerCase().trim(), n = 0;
      wadah.querySelectorAll("[data-cari]").forEach(function (el) {
        var cocok = !q || el.dataset.cari.indexOf(q) >= 0;
        el.hidden = !cocok;
        if (cocok) n++;
      });
      var info = kotak.parentNode.querySelector("[data-jumlah]");
      if (info) info.textContent = n + " " + info.dataset.jumlah;
      var kosong = (wadah.parentNode || wadah).querySelector(".tak-cocok");
      if (kosong) kosong.hidden = n > 0;
    });
  }

  /* ------------- foto yang dipilih tapi belum disimpan ------------- */
  function pasangPratinjauFoto() {
    document.querySelectorAll("input[data-pratinjau-foto]").forEach(function (masukan) {
      var wadah = document.getElementById(masukan.dataset.pratinjauFoto);
      if (!wadah) return;
      var alamat = [];
      masukan.addEventListener("change", function () {
        alamat.forEach(function (u) { URL.revokeObjectURL(u); });
        alamat = [];
        wadah.textContent = "";
        Array.prototype.forEach.call(masukan.files || [], function (berkas) {
          var fig = document.createElement("figure");
          var img = document.createElement("img");
          var u = URL.createObjectURL(berkas);
          alamat.push(u);
          img.src = u;
          img.alt = "";
          var cap = document.createElement("figcaption");
          cap.textContent = berkas.name;
          fig.appendChild(img);
          fig.appendChild(cap);
          wadah.appendChild(fig);
        });
        if (masukan.files && masukan.files.length) {
          var info = document.createElement("div");
          info.className = "petunjuk";
          info.style.flexBasis = "100%";
          info.textContent = masukan.files.length + " foto siap diunggah — tekan Simpan.";
          wadah.appendChild(info);
        }
      });
    });
  }

  /* ---------- rincian Akta Ikrar Wakaf & Pengesahan Nazhir ---------- */
  /* Pratinjau frasa Menimbang SK huruf b dan c. Susunannya harus sama dengan
     frasa_akta_ikrar / frasa_pengesahan_nazhir di konteks.py. */
  var BULAN = ["Januari", "Februari", "Maret", "April", "Mei", "Juni", "Juli",
               "Agustus", "September", "Oktober", "November", "Desember"];
  var NAMA_AKTA = {AIW: "Akta Ikrar Wakaf", APAIW: "Akta Pengganti Akta Ikrar Wakaf"};

  function tanggalPanjang(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    return m ? m[3] + " " + BULAN[+m[2] - 1] + " " + m[1] : "";
  }

  function pasangRincianBaku() {
    var blok = {};
    document.querySelectorAll("[data-rincian-baku]").forEach(function (b) {
      blok[b.dataset.rincianBaku] = b;
    });
    if (!Object.keys(blok).length) return;

    function nilai(b, kolom) {
      var el = b.querySelector('[data-rincian="' + kolom + '"]');
      return el ? el.value.trim() : "";
    }
    function gabung(daftar) { return daftar.filter(Boolean).join(" "); }
    function oleh(b, akta) {
      var nama = nilai(b, "pejabat"), wil = nilai(b, "wilayah_pejabat");
      var jabatan = "Pejabat Pembuat " + akta + (wil ? " " + wil : "");
      return nama ? nama + " selaku " + jabatan : jabatan;
    }
    function frasa(kategori, b) {
      var ada = ["nomor", "tanggal", "pejabat", "wilayah_pejabat"].some(function (k) {
        return nilai(b, k);
      });
      if (!ada) return "";
      var tgl = tanggalPanjang(nilai(b, "tanggal")), nomor = nilai(b, "nomor");
      if (kategori === "akta_ikrar") {
        var akta = NAMA_AKTA[nilai(b, "jenis")] || NAMA_AKTA.AIW;
        return gabung([akta, tgl && "tanggal " + tgl, nomor && "Nomor " + nomor,
                       "yang dibuat oleh " + oleh(b, akta)]);
      }
      return gabung(["oleh " + oleh(b, "Akta Ikrar Wakaf"), tgl && "tanggal " + tgl,
                     nomor && "Nomor " + nomor]);
    }
    function segarkan(kategori) {
      var b = blok[kategori], sasaran = b && b.querySelector("[data-frasa]");
      if (!sasaran) return;
      var f = frasa(kategori, b);
      if (f) sasaran.textContent = f;           // tanpa rincian: biarkan teks dari server
      var ur = b.querySelector("textarea");
      if (ur && f) {
        ur.placeholder = kategori === "akta_ikrar" ? f
          : "Surat Pengesahan Nazhir yang disahkan " + f;
      }
    }

    Object.keys(blok).forEach(function (kategori) {
      blok[kategori].addEventListener("input", function () { segarkan(kategori); });
      blok[kategori].addEventListener("change", function () { segarkan(kategori); });
    });

    var tombol = document.querySelector("[data-salin-ppaiw]");
    if (tombol && blok.akta_ikrar && blok.pengesahan_nazhir) {
      tombol.addEventListener("click", function () {
        ["pejabat", "wilayah_pejabat"].forEach(function (k) {
          var dari = blok.akta_ikrar.querySelector('[data-rincian="' + k + '"]');
          var ke = blok.pengesahan_nazhir.querySelector('[data-rincian="' + k + '"]');
          if (dari && ke && dari.value.trim()) ke.value = dari.value.trim();
        });
        segarkan("pengesahan_nazhir");
      });
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    pasangTab();
    pasangBarisDinamis();
    pasangWilayah();
    pasangLuas();
    pasangSaring();
    pasangKonfirmasi();
    pasangLipat();
    pasangSaringLipat();
    pasangPratinjauFoto();
    pasangRincianBaku();
  });
})();
